"""
This script goes to the bechdeltest.com website, pulls html data from every movie that they have reviewed,
and then pulls from that html data the movie title, and Bechdel rank from the page for the movie the page
corresponds with. It then writes that data into a text file for training the Bechdel test classification
algorithm.
"""

from urllib import request, error
import re


outfile = open('Bechdel_Data2','w')
datalines = []
datalines.append(("{:50}{:7}{}\n\n".format("TITLE",'YEAR','SCORE')))

for x in range(1,6830):
    url = "http://www.bechdeltest.com/view/"+str(x)+"/"
    try:
        raw_text = request.urlopen(url).read().decode("iso-8859-1")
        error_check = re.search(r'No such movie!',raw_text)
        if not error_check:
            movie_title = re.search(r'<title>(.*?) - Bechdel Test Movie List</title>', raw_text).group(1)
            movie_year = re.search(r'\((\d{4})\)</span>', raw_text).group(1)
            bechdel_score = re.search(r'alt="\[\[(\d)\]\]"', raw_text).group(1)
            datalines.append("{:100}{:7}{}\n".format(movie_title
                                                    .replace('&#39;',"'")
                                                    .replace('&amp;','&'), movie_year, bechdel_score))
    except error.HTTPError as er:
        if er.code == 404:
            print('404 error at http://www.bechdeltest.com/view/'+str(x))
            continue
        else:
            continue
    except error.URLError as er:
        if er.errno == 111:
            print("Connection Refused")
        else:
            continue

outfile.writelines(datalines)