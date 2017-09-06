import curses, curses.textpad
from processes import Manager

## Based on https://github.com/LyleScott/Python-curses-Scrolling-Example/blob/master/curses_scrolling.py
class Console(Manager):
    DOWN = 1
    UP = -1
    SPACE_KEY = 32
    ESC_KEY = 27
    
    PREFIX_SELECTED = '_X_'
    PREFIX_DESELECTED = '___'

    outputLines = []
    screen = None

    COMMAND_ROW = 11
    RESULTS_ROW = 12
    RESULTS_LEN = 10
    
    def __init__(self, screen):
        Manager.__init__(self, False)
        
        self.screen = screen

        self.screen.border(0)
        self.topLineNum = 0
        self.highlightLineNum = 0
        self.markedLineNums = []

        self.textwin, self.textbox = maketextbox(self.screen, 1, 80, self.COMMAND_ROW, 1, "")
        self.results = curses.newwin(self.RESULTS_LEN, 80, self.RESULTS_ROW, 1)

        self.result_lines = []
        
        self.getOutputLines()
        self.run()

    def do_quit(self, line):
        curses.endwin()
        return True

    def write(self, text):
        self.result_lines.append(text)
        self.textwin.clear()

    def default(self,line) :
	self.write("Don't understand '" + line + "'")

    def run(self):
        while True:
            self.displayScreen()
            # get user command
            c = self.screen.getch()
            if c == curses.KEY_UP:
                self.updown(self.UP)
            elif c == curses.KEY_DOWN:
                self.updown(self.DOWN)
            elif c == self.SPACE_KEY:
                self.markLine()
            elif c == self.ESC_KEY:
                exit()
            elif chr(c) in key_commands:
                key_commands[chr(c)](self)
            elif c == ord(';'):
                text = self.textbox.edit()
                self.onecmd(text)

    def markLine(self):
        linenum = self.topLineNum + self.highlightLineNum
        if linenum in self.markedLineNums:
            self.markedLineNums.remove(linenum)
        else:
            self.markedLineNums.append(linenum)

    def getOutputLines(self):
        mngr = Manager(True)
        mngr.do_show(None)
        self.outputLines = []
        for command in mngr.unique:
            self.outputLines.append("%d: %s" % (mngr.commands.count(command), command))
        
        self.nOutputLines = len(self.outputLines)

    def displayScreen(self):
        # clear screen
        self.screen.erase()

        # now paint the rows
        top = self.topLineNum
        bottom = self.topLineNum+curses.LINES
        for (index,line,) in enumerate(self.outputLines[top:bottom]):
            linenum = self.topLineNum + index
            if linenum in self.markedLineNums:
                prefix = self.PREFIX_SELECTED
            else:
                prefix = self.PREFIX_DESELECTED

            line = '%s %s' % (prefix, line,)

            # highlight current line
            if index != self.highlightLineNum:
                self.screen.addstr(index, 0, line)
            else:
                self.screen.addstr(index, 0, line, curses.A_BOLD)

        self.screen.refresh()

        self.results.addstr(0, 0, '\n'.join(self.result_lines))
        self.results.refresh()
                
    # move highlight up/down one line
    def updown(self, increment):
        nextLineNum = self.highlightLineNum + increment
        
        # paging
        if increment == self.UP and self.highlightLineNum == 0 and self.topLineNum != 0:
            self.topLineNum += self.UP
            return
        elif increment == self.DOWN and nextLineNum == curses.LINES and (self.topLineNum+curses.LINES) != self.nOutputLines:
            self.topLineNum += self.DOWN
            return
        
        # scroll highlight line
        if increment == self.UP and (self.topLineNum != 0 or self.highlightLineNum != 0):
            self.highlightLineNum = nextLineNum
        elif increment == self.DOWN and (self.topLineNum+self.highlightLineNum+1) != self.nOutputLines and self.highlightLineNum != curses.LINES:
            self.highlightLineNum = nextLineNum

def generate(console):
    text = console.textbox.edit()
    console.write(text)

def aggregate(console):
    console.write("This is a test.")

key_commands = {'g': generate, 'a': aggregate}

## From https://gist.github.com/interstar/3005137
def maketextbox(screen, h,w,y,x,value="",deco=None,textColorpair=0,decoColorpair=0):
    # thanks to http://stackoverflow.com/a/5326195/8482 for this
    nw = curses.newwin(h,w,y,x)
    txtbox = curses.textpad.Textbox(nw,insert_mode=True)
    if deco=="frame":
        screen.attron(decoColorpair)
        curses.textpad.rectangle(screen,y-1,x-1,y+h,x+w)
        screen.attroff(decoColorpair)
    elif deco=="underline":
        screen.hline(y+1,x,underlineChr,w,decoColorpair)
        
    nw.addstr(0,0,value,textColorpair)
    nw.attron(textColorpair)
    screen.refresh()
    return nw,txtbox
        
curses.wrapper(Console)

def maintenance():
    # When is the last time we collected mortality?
    pass

def read_log():
    laststatus = {} # {(project, task): (datetime, status)}
    with open('console.log', 'r') as fp:
        for line in fp:
            parts = line.split()
            datetime = parts[0]
            project = parts[1]
            task = parts[2]
            status = parts[3:].join()

            laststatus[project, task] = (datetime, status)

    return laststatus
