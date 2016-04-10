__author__ = "Mitch Powell"

ResultFile = open('Bechdel_Data','r')
titles = []
ResultFile.readline()
ResultFile.readline()
for line in ResultFile.readlines():
    if len(line) > 0:
        titles.append(line.split(',')[0].strip())

print(titles)