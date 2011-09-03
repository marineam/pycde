#

"""Text User Interface"""

import sys

class TextUI(object):

    def choose(self, name, items, fmt=str):
        if len(items) == 1:
            print "Found %s: %s" % (name, fmt(items[0]))
            return items[0]
        else:
            print '%ss:' % name
            for i, item in enumerate(items):
                formated = fmt(item).replace('\n', '\n     ')
                print ' %2d. %s' % (i+1, formated)
            choice = int(raw_input('Choose %s: ' % name))
            return items[choice - 1]

    def status(self, text):
        print text

    def info(self, text):
        print text

    def error(self, text):
        sys.stderr.write('%s\n' % text)
