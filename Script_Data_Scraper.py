"""
This script runs through every title in the Bechdel_Data list, and checks if there is a script for it
on the Internet Movie Script Database. If there is, then it extracts the script from the HTML, and
writes it to a file in the SCRIPT_PATH for use in the solver algorithm.
"""

from urllib import request, error
from bs4 import BeautifulSoup
import re


__author__ = "Mitch Powell"

# The path for the script files to be put into
SCRIPT_PATH = '/home/mitch/Misc_Programming/NLP/Bechdel/Scripts/'

# Open the Bechdel_Data file, instantiate a title array, skip the first two lines.
ResultFile = open('Bechdel_Data','r')
titles = []
ResultFile.readline()
ResultFile.readline()


def write_script(script, title):
    scriptfile = open(SCRIPT_PATH+title+'.script','w')
    scriptfile.write(script)
    scriptfile.close()

# Take every title out of the Bechdel_Data file and put it in the titles list
for line in ResultFile.readlines():
    if len(line) > 0:
        title = line.split(',')[0].strip()
        titles.append(title)

# Try to find a
for title in titles:
    mod_title = '-'.join(title.split())
    url = 'http://www.imsdb.com/scripts/'+mod_title+'.html'

    # Catches HTTP and URL Errors
    try:
        script = request.urlopen(url).read().decode('iso-8859-1')
        if not re.search(r'<pre></pre>',script):
            soup = BeautifulSoup(''.join(script))
            raw_script = str(soup.find('pre'))
            script_text = BeautifulSoup(raw_script).get_text()
            write_script(script_text,title)
    # Seems as though internet movie script database specifically removes the movies for which a 404 error occurs
    except error.HTTPError as er:
        print(er.code,title)
        continue
    except error.URLError as er:
        print(er.errno,title)
        continue

