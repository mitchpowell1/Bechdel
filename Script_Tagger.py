import nltk
import re
from urllib import request
from bs4 import BeautifulSoup


###
# This function reads a movie script and pulls out the names of characters. The regular expressions will cause issues
# if the movie script is not formatted well, however.
###
def get_popular_characters(script_name):
    sample_script = open(script_name, 'r')
    sample_script_lines = [line.strip() for line in sample_script.split('\n') if len(line) > 0]

    patterns = [
        (r'^INT\..*?$|^EXT\..*?$', 'S'),
        (r'^[A-Z\.\-]+$|^[A-Z\.\-]+\s*[A-Za-z]+$', 'C')
    ]

    retagger = nltk.RegexpTagger(patterns)

    characters = [char for char, tag in retagger.tag(sample_script_lines) if tag == "C"]
    character_freqs = nltk.FreqDist(characters)
    top_characters = [character for character, freq in character_freqs.most_common(20)]
    return top_characters


###
# Defined this because I found myself doing it a lot. Was attempting not to reuse too much code.
###
def open_script(movie):
    return open('./Scripts/'+movie+".script").read()


###
# This function checks the indentation of a script to determine if it is "well-formatted".
# here, we consider a movie to be well formatted if over 90% of the lines in the script fall into one of
# the three most common indentation levels.
###
def is_well_formatted(movie):
    script = open_script(movie)
    scriptlines = [line for line in script.split('\n') if len(line.strip())>0]
    indentations = [len(line)-len(line.lstrip()) for line in scriptlines]
    indentation_frequencies = nltk.FreqDist(indentations)
    most_common = [key for key, value in indentation_frequencies.most_common(3)]
    if len(most_common) < 3:
        return False
    formatted_lines = 0
    for line in scriptlines:
        if len(line)-len(line.lstrip()) in most_common:
            formatted_lines += 1
    return formatted_lines/len(scriptlines) > .9


###
# This tag_lines function is takes a movie name as input, and assuming that it is well-formatted, parses every line,
# and assigns it a tag based upon its indentation level (and parenthesis, in the case of meta-data).
#
# Possible Tags are:
#   "S": Scene Boundary
#   "N": Scene Description
#   "M": Meta Data
#   "C": Character Mention
#   "D": Dialog
###
def tag_lines(movie):
    script = open_script(movie)
    scriptlines = [line for line in script.split('\n') if len(line.strip()) > 0]
    indentations = [len(line)-len(line.lstrip()) for line in scriptlines]
    indentation_frequencies = nltk.FreqDist(indentations)
    important_levels = sorted([key for key, value, in indentation_frequencies.most_common(4)])
    tagged_lines = []
    for line in range(len(scriptlines)):
        if indentations[line] == important_levels[0]:
            if re.match(r'^(EXT\..*|INT\..*)$',scriptlines[line].strip()):
                tagged_lines.append((scriptlines[line], "S"))
            else:
                tagged_lines.append((scriptlines[line], "N"))
        elif indentations[line] == important_levels[1]:
            tagged_lines.append((scriptlines[line], "D"))
        elif indentations[line] == important_levels[2]:
            tagged_lines.append((scriptlines[line], "M"))
        elif indentations[line] == important_levels[3]:
            if re.match(r'^\(.+\)$',scriptlines[line].strip()):
                tagged_lines.append((scriptlines[line], "M"))
            else:
                tagged_lines.append((scriptlines[line], "C"))
        else:
            tagged_lines.append((scriptlines[line], "U"))
    return tagged_lines


###
# This function extracts a list of character names from a well-ordered movie script
###
def get_chars(movie):
    script = open("./Scripts/"+movie+".script").read()
    chars = set(re.findall(r'^[A-z\.\-]+$|\n\s*[A-Z\.\-]+\s*[A-Za-z]+\n', script))
    for char in chars:
        if "INT." not in char and "EXT." not in char:
            print(char.strip())


###
# This creates and returns a Naive bayes classifier that is trained on a corpus of names and is then
# used as a backoff if finding the actor/actress who played a character on bing does not work.
###
def make_classifier():
    from nltk.corpus import names

    training_names = [(name,'male') for name in names.words('male.txt')] +\
                     [(name,'female') for name in names.words('female.txt')]
    feature_sets = [(name_features(name), gender) for (name, gender) in training_names]
    classifier = nltk.NaiveBayesClassifier.train(feature_sets)
    return classifier


###
# This name_features method is used by the gender classifier in order to determine the gender of a name
# (This is used as a backoff from the bing-powered gender classification
###
def name_features(name):
    features = {
        'last_letter': name[-1],
        'first_letter': name[0],
        'name': name
    }
    for letter in 'abcdefghijklmnopqrstuvwxyz':
        features["count({})".format(letter)] = name.lower().count(letter)
        features["has({})".format(letter)] = (letter in name.lower())
    if len(name) > 1:
        features['last_two'] = name[-2:]
        features['first_two'] = name[:2]
    if len(name) > 2:
        features['last_three'] = name[-3:]
        features['first_three'] = name[:3]
    return features


###
# Uses bing to try to determine the gender of a character on the basis of the gender of the person who played
# them in the movie
#
# Accepts a movie name, a trained name classifier, and a list of characters as input
# Returns a dictionary of characters to their classified genders.
###
def classify_genders_bing(movie, backupclassifier, characterlist):
    char_gends = {}
    for character in characterlist:
        url = "http://www.bing.com/search?q=who+plays+" + '+'.join(character.split(' ')) + "+in+" + "+".join(
            movie.replace("'", "").split(' '))
        raw_html = request.urlopen(url).read().decode('utf-8')
        soup = BeautifulSoup(raw_html)
        gender = ''
        # The subtitle on the bing results b_content box often contains "Actor or Actress"
        subtitle = soup.find('div', {'class': 'b_entitySubTitle'})
        actor_snippet = soup.find('div', {'class': 'b_lBottom'})
        # If the subtitle exists
        if subtitle is not None:
            sub_text = subtitle.get_text()
            if 'Actor' in sub_text:
                gender = 'male'
            elif 'Actress' in sub_text:
                gender = 'female'
        # If there is no subtitle
        else:
            title = soup.find('h2',{'class': 'b_entityTitle'})
            # The b_context box often contains a little tidbit about the life of the actor/actress (This is useful if
            # they are listed as a "comedian" or "singer" or something along those lines
            if actor_snippet is not None:
                snip = actor_snippet.get_text()
                if 'actress' in snip.lower():
                    gender = "female"
                elif 'actor' in snip.lower():
                    gender = 'male'
            # The names of the actors/actresses are often more useful in the classification of the gender than the
            # names of the characters, so we classify their names if we can find them.
            elif title is not None:
                if len(title.get_text().split()) == 2:
                    gender=backupclassifier.classify(name_features(title.get_text().split()[0].lower()))
        # If we have come all this way without assigning a gender to the character, we go ahead and try to classify the
        # character by their name. This is often not a great means of gender classification, but it is presumably
        # better than nothing.
        if gender == '':
            gender=backupclassifier.classify(name_features(character.title()))
        char_gends[character] = gender
        print(character, gender)
    return char_gends


###
# Takes a movie name as input and determines whether or not the movie passes the
###
def passes_test_one(movie):
    character_list = get_popular_characters("./Scripts/" + movie + ".script")
    gender_classifier = make_classifier()
    char_genders = classify_genders_bing(movie, gender_classifier, character_list)
    female_chars = 0
    for char in character_list:
        if char_genders[char] == "female":
            female_chars += 1
    print("Num:",female_chars)
    return female_chars >= 2


def main():
    club = tag_lines("Mulan")
    for line, tag in club:
        if tag == "U":
            print(line)
    '''movies = [line.split(',')[0].strip() for line in open('Bechdel_Data','r').read().split('\n')]
    for movie in movies:
        try:
            if is_well_formatted(movie):
                print(movie)
        except FileNotFoundError:
            continue'''

# I want to be able to import these functions as a module in a separate .py file without running the main method.
if __name__ == "__main__":
    main()
