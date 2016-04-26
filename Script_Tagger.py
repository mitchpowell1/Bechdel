import nltk
import re
from urllib import request
from bs4 import BeautifulSoup


###
# This function reads a movie script and pulls out the names of characters. The regular expressions will cause issues
# if the movie script is not formatted well, however.
###
def get_popular_characters(character_list):
    character_freqs = nltk.FreqDist(character_list)
    top_characters = [character for character, freq in character_freqs.most_common(20)]
    return top_characters


###
# Defined this because I found myself doing it a lot. Was attempting not to reuse too much code.
###
def open_script(movie):
    script = open('./Scripts/'+movie+".script").read()
    return script


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
    percentage = formatted_lines/len(scriptlines)
    #print(percentage)
    # Reject any movies whose percentage of lines on common indentation levels does not fall between 90 and 99.5 percent
    return .9 < percentage < .995


###
# Sanity check: Checks if the character names, scene boundaries and dialog line up as you would expect in a typical
# script. E.g. Scene descriptions after scene boundaries, dialog after character names, character names occur between
# scene boundaries
###
def sanity_check(tagged_lines):
    tags = []
    strange_tags = 0
    for x in range(len(tagged_lines)):
        tags.append(tagged_lines[x][1])
        # Scene boundaries should be followed by either a scene description or a character name
        if tagged_lines[x][1] == "S":
                if tagged_lines[x+1][1] not in ["N","C"]:
                    strange_tags += 1
        # Dialog lines should occur after Character names, and the only lines in between should be
        # meta-information, scene descriptions, or other dialog lines.
        if tagged_lines[x][1] == "D":
            character_name_found = False
            start_node = x-1
            while start_node >= 0 and not character_name_found:
                if tagged_lines[start_node][1] == "C":
                    character_name_found = True
                else:
                    if tagged_lines[start_node][1] not in "MND":
                        strange_tags+=1
                    start_node -= 1
    #print("Strange Tags:",strange_tags)
    #print("Strange Tag Ratio:", round(100*(strange_tags/len(tagged_lines)), 2))
    return 100*(strange_tags/len(tagged_lines)) < 10


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
    important_levels = sorted([key for key, value, in indentation_frequencies.most_common(5)])
    tagged_lines = []
    for line in range(len(scriptlines)):
        if indentations[line] == important_levels[0]:
            if re.match(r'^([\d\.]{2,})?\s*(EXT\.?.*|INT\.?.*)$',scriptlines[line].strip()):
                tagged_lines.append((scriptlines[line], "S"))
            else:
                tagged_lines.append((scriptlines[line], "N"))
        elif indentations[line] == important_levels[1]:
            tagged_lines.append((scriptlines[line], "D"))
        elif indentations[line] == important_levels[2]:
            tagged_lines.append((scriptlines[line], "M"))
        elif indentations[line] == important_levels[3]:
            if re.match(r'^\(.+\)| .+\) | \(.+$',scriptlines[line].strip()):
                tagged_lines.append((scriptlines[line], "M"))
            else:
                tagged_lines.append((scriptlines[line], "C"))
        elif indentations[line] == important_levels[4]:
            tagged_lines.append((scriptlines[line], "M"))
        else:
            tagged_lines.append((scriptlines[line], "U"))
    sanity_check(tagged_lines)
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
#
# Note: This name_features function is a slight augmentation of the one that can be found in the NLTK
# online book at http://www.nltk.org/book/ch06.html
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
        try:
            url = "http://www.bing.com/search?q=who+plays+" + '+'.join(character.split(' ')) + "+in+" + "+".join(
                movie.replace("'", "").split(' '))
            raw_html = request.urlopen(url).read().decode('utf-8')
            soup = BeautifulSoup(raw_html)
            gender = ''
            if len(character) == 0:
                gender = "male"
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
        except UnicodeEncodeError:
            char_gends[character] = backupclassifier.classify(name_features(character.title()))
    return char_gends


###
# Takes a movie name as input and determines whether or not the movie passes the
###
def passes_test_one(characters, gender_map):
    females = 0
    for character in characters:
        if gender_map[character] == "female":
            #print(character)
            females += 1
    #print("Named Female Characters:",females)
    return females >= 2


###
# Extracts a character name from a character-mention line in a movie script (this is useful because sometimes
# movie scripts have some meta data associated with them, and that's pretty uncool
###
def extract_character_names(character_line):
    if re.match(r'[A-Za-z\.\-]+.*\(.+\)?.*', character_line):
        character = re.findall(r'([A-Z\-\.\s]+)(\s*\(.*\))?', character_line)[0][0].strip()
    else:
        character = character_line.strip()
    return character


###
# This function takes a list of tagged lines as input, and returns a list of scenes
###
def split_by_scene(tagged_lines):
    scene = []
    scenes = []
    for line, tag in tagged_lines:
        if tag == "S":
            scenes.append(scene)
            scene = []
        scene.append((line,tag))
    return scenes


###
# This function is used to compile a list of movies that are both well-formatted, and whose parse passes
# the sanity check.
###
def get_parseable_movies():
    bechdel_list = open("Bechdel_Data","r")
    parseable_scripts = open("Parseable", "w")
    movies = [line.split(',')[0].strip() for line in bechdel_list.readlines()]
    for movie in movies:
        try:
            if is_well_formatted(movie) and sanity_check(tag_lines(movie)):
                parseable_scripts.write(movie+"\n")
        except FileNotFoundError:
            continue


###
# This function evaluates how good the performance of the classifier is for test One.
###
def evaluate_test_one():
    moviesfile = open("Bechdel_Data", 'r')
    testfile = open("t1",'r')
    moviesfile.readline()
    bechdel_scores = {}
    visited = {}
    total = 0
    true_pos = 0
    false_pos = 0
    true_neg = 0
    false_neg = 0
    for line in moviesfile:
        if len(line.split(',')) == 3:
            data = line.split(',')
            movie = data[0].strip()
            score = data[2].strip()
            bechdel_scores[movie] = score
    for line in testfile:
        data = line.split(',')
        movie = data[0].strip()
        if not visited.get(movie):
            visited[movie] = True
            total+=1
            passes_test = data[1].strip() == "True"
            # print(movie, passes_test)
            # If the classifier evaluates that the movie passes the first test
            if passes_test:
                # Check if the data agrees
                # True Positive:
                if int(bechdel_scores[movie]) > 0:
                    true_pos += 1
                # False positive
                else:
                    false_pos += 1
            # If the classifier evaluates that the movie failed the first test
            else:
                # True Negative:
                if int(bechdel_scores[movie]) == 0:
                    true_neg += 1
                # False Negative:
                else:
                    false_neg += 1
        else:
            print(movie)
    print("Total: "+str(total))
    print("True Positives: "+str(true_pos))
    print("True Negatives: "+str(true_neg))
    print("False Positives: "+str(false_neg))
    print("False Negatives: "+str(false_neg))
    print("Accuracy: "+str((true_pos+true_neg)/total))


###
# Performs the first Bechdel test and writes the results to a datafile. I do it this way because the first test takes
# a very long time, since it has to gather data from Bing
###
def perform_test_one():
    moviesfile = open("Parseable",'r')
    movies = [movie.strip() for movie in moviesfile.readlines()]
    gender_classifier = make_classifier()
    testoneresults = open("Test_One_Results",'w')
    for movie in movies:
        tagged_lines = tag_lines(movie)
        char_lines = [line.strip() for line, tag in tagged_lines if tag == "C"]
        chars = get_popular_characters([extract_character_names(char) for char in char_lines])
        genders = classify_genders_bing(movie, gender_classifier, chars)
        print(movie+" passes test one: "+str(passes_test_one(chars,genders)))
        testoneresults.write(movie+", "+str(passes_test_one(chars,genders))+"\n")
    testoneresults.close()


###
# The process of looking up character genders was slow, so I made this method to make local character files for each
# of my "parseable" movie scripts so that I did not have to go look up the character genders every time I wanted to
# run tests on the scripts.
###
def make_genders_files():
    moviesfile = open("Parseable",'r')
    movies = [movie.strip() for movie in moviesfile.readlines()]
    gender_classifier = make_classifier()
    for movie in movies:
        charfile = open("./Characters/"+movie, "w")
        tagged_lines = tag_lines(movie)
        char_lines = [line.strip() for line, tag in tagged_lines if tag =="C"]
        chars = get_popular_characters([extract_character_names(char) for char in char_lines])
        genders = classify_genders_bing(movie, gender_classifier, chars)
        for character in chars:
            charfile.write(character+","+genders[character]+"\n")


def passes_test_two(tagged_lines):
    scenes = split_by_scene(tagged_lines)
    for scene in scenes:
        char_lines = [line for line, tag in scene if tag == "C"]
        if len(char_lines) > 0:
            print(extract_character_names(char_lines[0].strip()))


def main():
    """movie = "Fight Club"
    movie_lines = tag_lines("Fight Club")
    passes_test_two(movie_lines)"""

# I want to be able to import these functions as a module in a separate .py file without running the main method.
if __name__ == "__main__":
    main()
