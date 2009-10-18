from graphics import *
from appuifw import *
from e32calendar import *
import sys, e32, e32calendar, time, key_codes, appuifw, telephone, contacts, string, os, globalui, graphics
import pickle, dir_iter, re, cProfile

# PyS60EbookReader - version 0.3
def cmp_file(a, b):
    return cmp(a, b)
    if a[0] < b[0]:
        return 1
    elif a[0] > b[0]:
        return -1
    else:
        return 0

class DocInfo():
    def __init__(self):
        self.file_list = []
        self.last_file = ""
        self.docinfo_filename = "e:\\data\\bookview-docinfo.conf"
        self.Load()

    def Load(self):
        if os.path.exists(self.docinfo_filename):
            f = file(self.docinfo_filename, "rb")
            content = pickle.load(f)
            f.close()
            self.file_list = content[0]
            self.last_file = content[1]

    def Save(self):
        f = file(self.docinfo_filename, "wb")
        content = [self.file_list, self.last_file]
        pickle.dump(content, f)
        f.close()

    def GetLastPos(self, filename):
        for f in self.file_list:
            if f[0] == filename:
                return f[1]
        return 0

    def SetLastPos(self, filename, pos):
        for f in self.file_list:
            if f[0] == filename:
                f[1] = pos
                return None
        self.file_list.append([filename, pos])

    def GetLibrary(self):
        books = []
        for fname in self.file_list:
            filesize = os.path.getsize(fname[0])
            books.append( (unicode(fname[0]), unicode(round(fname[1] / float(filesize) * 100, 2))+u'%') )
        return books

class EnvironmentSaver():
    def __init__(self):
        self.prev_exithandler = app.exit_key_handler
        self.prev_app_menu = app.menu
        self.prev_app_body = app.body
        self.prev_screen_type = app.screen

    def Restore(self):
        app.exit_key_handler = self.prev_exithandler
        app.menu = self.prev_app_menu
        app.body = self.prev_app_body
        app.screen = self.prev_screen_type

class FileBrowser:
    def __init__(self):
        self.script_lock = e32.Ao_lock()
        self.dir_stack = []
        self.current_dir = dir_iter.Directory_iter(e32.drive_list())
        self.success = False
        self.one_row_filelist = False
        if self.one_row_filelist:
            self.lb = Listbox([u'content'], self.lbox_observe)
        else:
            self.lb = Listbox([(u'content', u'desc')], self.lbox_observe)

    def SetDir(self, dir):
        parts = string.split(dir, '\\')
        #self.dir_stack = []
        #for p in parts:
        #    self.current_dir.add(p)
        #    self.dir_stack.append(p)
        #print os.listdir(dir)
        #files = os.listdir(dir)
        #for i in range(len(files)):
        #    files[i] = unicode(files[i])

    def run(self):
        self.prev_env = EnvironmentSaver()
        self.ShowContentOfCurrentDir(0)
        app.exit_key_handler = self.destroy
        app.menu = [(u'Open', self.lbox_observe), (u'Close', self.destroy)]
        app.screen='normal'
        app.body = self.lb
        self.script_lock.wait()
    def destroy(self):
        self.prev_env.Restore()
        self.script_lock.signal()

    def lbox_observe(self, ind = None):
        if not ind == None:
            index = ind
        else:
            index = self.lb.current()
        focused_item = 0

        if self.current_dir.at_root:
            self.dir_stack.append(index)
            self.current_dir.add(index)
        elif index == 0:                              # ".." selected
            focused_item = self.dir_stack.pop()
            self.current_dir.pop()
        elif os.path.isdir(self.current_dir.entry(index-1)):
            self.dir_stack.append(index)
            self.current_dir.add(index-1)
        else:
            item = self.current_dir.entry(index-1)
            self.filename = item
            self.success = True
            self.destroy()
        self.ShowContentOfCurrentDir(focused_item)

    def ShowContentOfCurrentDir(self, focused_item):
        entries = []
        if self.one_row_filelist:
            entries = self.current_dir.list_repr()
            for i in range(len(entries)):
                entries[i] = entries[i][0]
            if not self.current_dir.at_root:
                entries.insert(0, u"..")
        else:
            entries = self.current_dir.list_repr()
            if not self.current_dir.at_root:
                entries.insert(0, (u"..", u""))
        #entries.sort(cmp_file)
        self.lb.set_list(entries, focused_item)

def strip_text(text):
    global re_tag, re_tag2
    text = unicode(text, 'utf8', 'replace')

    #text = text.replace("<p>", "")
    #text = text.replace("</p>", "")
    #text = text.replace("<P>", "")
    #text = text.replace("</P>", "")
    text = text.replace("\n", "")
    text = text.replace("\r", "")

    text = re_tag.sub('', text)
    text = re_tag2.sub(' ', text)

    '''
    text = text.replace("<strong>", "")
    text = text.replace("</strong>", "")
    text = text.replace("<emphasis>", "")
    text = text.replace("</emphasis>", "")
    text = text.replace("<strikethrough>", "")
    text = text.replace("</strikethrough>", "")
    text = text.replace("<sub>", "")
    text = text.replace("</sub>", "")
    text = text.replace("<sup>", "")
    text = text.replace("</sup>", "")
    text = text.replace("<code>", "")
    text = text.replace("</code>", "")
    text = text.replace("<section>", "")
    text = text.replace("</section>", "")
    '''
    text = string.strip(text)

    return text

def create_format_map(text):
    # do the formating map:
    format_map = []
    strong_pos = text.find("<strong>")
    while strong_pos >= 0:
        format_map.append([strong_pos, FONT_BOLD])
        strong_pos = text.find("<strong>", strong_pos+8)
    strong_pos = text.find("</strong>")
    while strong_pos >= 0:
        format_map.append([strong_pos, 0])
        strong_pos = text.find("</strong>", strong_pos+9)
    return format_map

class Document:
    def __init__(self, filename, config):
        if not os.path.exists(filename):
             return None
        self.name = "Document"
        self.filename = filename
        self.handle = file(self.filename, "rb")
        self.filesize = os.path.getsize(self.filename)
        self.config = config

    def SetPos(self, pos):
        self.handle.seek(pos)

    def GetPos(self):
        return self.handle.tell()

    def GetRelativePos(self):
        return round(self.handle.tell() / float(self.filesize) * 100, 2)

    def divide_text_by_pix_nums(self, text, desired_width):
        lines = []
        start_of_text = 0
        last_space_pos = 0
        while last_space_pos > -1:
            space_pos = text.find(' ', last_space_pos+1)
            if app.body.measure_text(strip_text(text[start_of_text:space_pos]),
                                     (self.config.font, self.config.font_size, FONT_ANTIALIAS))[0][2] > desired_width:
            #if test(text[start_of_text:space_pos]) > desired_width:
                lines.append(text[start_of_text:last_space_pos])
                start_of_text = last_space_pos
                last_space_pos = space_pos
            else:
                last_space_pos = space_pos
        lines.append(text[start_of_text:])
        return lines

    def get_prev_line(self):
        buffer_size = 50
        pos = -1
        text = ""
        text_to_prepend = ""
        on_the_begining_of_file = False
        while True:
            on_the_begining_of_file = False
            if self.handle.tell() - buffer_size < 0:
               # Start of file
               on_the_begining_of_file = True
               remaining_chars = self.handle.tell()
               self.handle.seek(0)
               text = self.handle.read(remaining_chars) + text
               self.handle.seek(0)
            else:
               # somewhere inside file
               self.handle.seek(-buffer_size, 1)
               text_to_prepend = self.handle.read(buffer_size)
               text =  text_to_prepend + text
               self.handle.seek(-buffer_size, 1)
            pos = text_to_prepend.rfind('\n')
            if pos > -1 or on_the_begining_of_file:
               break
        if pos > -1:
            self.handle.seek(+pos, 1)
            #print pos, '[', unicode(text_to_prepend[:pos], 'utf8', 'replace'), ']'
        return [text[text.rfind('\n')+1:] + '\n', on_the_begining_of_file]

    def GetNextNLines(self, n, desired_width):
        #print '[next-start', unicode(self.handle.read(14), 'utf8', 'replace'), ']'
        #self.handle.seek(-14, 1)

        lines = []
        #print "next", self.handle.tell(),
        while len(lines) < n:
            line = self.handle.readline(2000)
            lines += self.divide_text_by_pix_nums(line, desired_width)
        # seek to back
        if len(lines) > n:
            char_to_rewind = 0
            for line_to_rewind in lines[n:]:
                char_to_rewind += len(line_to_rewind)
            self.handle.seek(self.handle.tell()-char_to_rewind)
        #print self.handle.tell()
        #print '[next-end', unicode(self.handle.read(14), 'utf8', 'replace'), ']'
        #self.handle.seek(-14, 1)

        return lines[:n]

    def GetPrevNLines(self, n, desired_width):
        #print '[prev-START', unicode(self.handle.read(14), 'utf8', 'replace'), ']'
        #self.handle.seek(-14, 1)
        #print "prev", self.handle.tell(),
        lines = []
        while len(lines) < n:
            res = self.get_prev_line()
            line = res[0]
            lines = self.divide_text_by_pix_nums(line, desired_width) + lines
            if res[1]:
                break
        # seek to back
        if res[1]:
            self.handle.seek(0)
            lines = self.GetNextNLines(n, desired_width)
            self.handle.seek(0)
        elif len(lines) > n:
            char_to_rewind = 0
            #for line_to_rewind in lines[:-3]:
            #    print '["', unicode(line_to_rewind, 'utf8', 'replace'), '"]'
            for line_to_rewind in lines[n:]:
                #print '["', unicode(line_to_rewind, 'utf8', 'replace'), '"]'
                char_to_rewind += len(line_to_rewind)
            #print self.handle.tell(),
            self.handle.seek(char_to_rewind, 1)
        #print self.handle.tell()
        #print '[prev-END', unicode(self.handle.read(14), 'utf8', 'replace'), ']'
        #self.handle.seek(-14, 1)
        return lines[:n]

    def Close(self):
        self.handle.close()

class Config:
    def __init__(self):
        self.config_filename = "e:\\Data\\bookview.conf"
        self.line_spacing = 19
        self.font_size = 18
        self.font_color = 0
        self.status_font_size = 10
        self.status_font_color = 0
        self.status_font = 'normal'
        self.background_color = 1
        self.font = 'legend'
        self.paragraph_spaces="   "
        self.offset = [5, 0, 5, 0]
        self.colors = [
                       [u'black', 0x000000],
                       [u'white', 0xffffff],
                       [u'dark yellow', 0x717100],
                       [u'yellow', 0xffff00],
                       [u'light yellow', 0xfff66a],
                       [u'dark blue', 0x212948],
                       [u'blue', 0x0000ff],
                       [u'light blue', 0xabc5f0],
                       [u'dark brown', 0x4c1b00],
                       [u'brown', 0xa4400a],
                       [u'orange', 0xeb8922],
                       [u'light orange', 0xffd096],
                       [u'dark green', 0x254f17],
                       [u'green', 0x00ff00],
                       [u'light green', 0x53de25],
                       [u'dark gray', 0x424242],
                       [u'gray', 0x808080],
                       [u'light gray', 0xc5c5c5],
                      ]
        self.Load()
    def Load(self):
        if os.path.exists(self.config_filename):
            f = file(self.config_filename, "rb")
            config_list = pickle.load(f)
            self.SetFromList(config_list)
            f.close()

    def GetAsList(self):
        res = [self.line_spacing, self.font_size, self.font_color,
               self.status_font_size, self.status_font_color,
               self.status_font, self.background_color,
               self.font, self.offset]
        return res

    def SetFromList(self, l):
        self.line_spacing = l[0]
        self.font_size = l[1]
        self.font_color = l[2]
        self.status_font_size = l[3]
        self.status_font_color = l[4]
        self.status_font = l[5]
        self.background_color = l[6]
        self.font = l[7]
        self.offset = l[8]
        return None

    def GetColor(self, num):
        return self.colors[num][1]

    def GetColorNames(self):
        names = []
        for c in self.colors:
            names.append(c[0])
        return names

    def GetNumericColor(self, name):
        for c in self.colors:
            if c[0] == name:
                return c[1]
        return 0x000000

    def GetFontIndex(self, font):
        fonts = [u'normal', u'dense', u'title', u'symbol', u'legend', u'annotation']
        for i in range(len(fonts)):
            if fonts[i] == font:
                return i
        return 0

    def RunDialog(self):
        app.screen = 'normal'

        fonts = [u'normal', u'dense', u'title', u'symbol', u'legend', u'annotation']
        fields = []
        fields.append( (u"Line spacing", 'number', self.line_spacing) )
        fields.append( (u"Font size", 'number', self.font_size) )
        fields.append( (u"Font family", 'combo', (fonts, self.GetFontIndex(self.font)) ) )
        fields.append( (u"Font color", 'combo', (self.GetColorNames(), self.font_color) ) )
        fields.append( (u"Background color", 'combo', (self.GetColorNames(), self.background_color) ) )
        fields.append( (u"Left offset", 'number', self.offset[0]) )
        fields.append( (u"Right offset", 'number', self.offset[2]) )
        fields.append( (u"Top offset", 'number', self.offset[1]) )
        fields.append( (u"Bottom offset", 'number', self.offset[3]) )
        fields.append( (u"Status font size", 'number', self.status_font_size ) )
        fields.append( (u"Status font family", 'combo', (fonts, self.GetFontIndex(self.status_font) ) ) )
        fields.append( (u"Status font color", 'combo', (self.GetColorNames(), self.status_font_color) ) )

        form = Form(fields, flags=FFormDoubleSpaced | FFormEditModeOnly)
        form.save_hook = self.Save
        form.execute()

    def Save(self, data):
        for d in data:
            if d[0] == u'Line spacing':
                self.line_spacing = int(d[2])
            elif d[0] == u'Font size':
                self.font_size = int(d[2])
            elif d[0] == u'Status font size':
                self.status_font_size = int(d[2])
            elif d[0] == u'Font family':
                self.font = str(d[2][0][d[2][1]])
            elif d[0] == u'Status font family':
                self.status_font = str(d[2][0][d[2][1]])
            elif d[0] == u'Font color':
                self.font_color = int(d[2][1])
            elif d[0] == u'Background color':
                self.background_color = int(d[2][1])
            elif d[0] == u'Status font color':
                self.status_font_color = int(d[2][1])
            elif d[0] == u'Left offset':
                self.offset[0] = int(d[2])
            elif d[0] == u'Right offset':
                self.offset[2] = int(d[2])
            elif d[0] == u'Top offset':
                self.offset[1] = int(d[2])
            elif d[0] == u'Bottom offset':
                self.offset[3] = int(d[2])
        f = file(self.config_filename, "wb")
        pickle.dump(self.GetAsList(), f)
        f.close()
        #self.status_font_size = int(data[)
        app.screen = 'large'
        #redraw_cb()
        return True

class Application:
    def __init__(self):
        # read configuration
        self.config = Config()
        self.doc_info = DocInfo()
        # fill menu
        app.menu = [(u'Recent files', self.ShowRecentFiles),
                    (u'Open file', self.OpenFile),
                    (u'Go to start', self.GoToStartOfFile),
                    (u'Preferences', self.config.RunDialog),
                    (u'Exit', self.Quit)]
        # keep backlight funcs
        self.backlight_timer = e32.Ao_timer()
        self.txt = ["Welcome to PyS60EbookReader!"," ",  "Use menu to open file..."]
        app.focus = self.GainFocus
        self.app_lock = e32.Ao_lock()
        app.exit_key_handler = self.Quit
        app.directional_pad = False
        self.BacklightOn()


        if self.doc_info.last_file != "":
            self.doc = Document(self.doc_info.last_file, self.config)
            if self.doc:
                last_pos = self.doc_info.GetLastPos(self.doc_info.last_file)
                print last_pos
                self.doc.SetPos(last_pos)
                self.prev_file_pos = last_pos
        else:
            self.doc = None
            self.prev_file_pos = 0

    def Run(self):
        canvas = Canvas(self.RedrawCB, self.EventCB)
        self.prev_event_get_prev = False
        self.prev_event_get_next = False
        app.screen='large'
        app.body = canvas
        app.name = "Book View in PyS60"
        if self.doc != None:
            self.txt = self.doc.GetNextNLines(self.get_max_number_of_lines(), self.get_max_line_width())
        self.RedrawCB(None)
        self.app_lock.wait()

    def BacklightOn(self):
        e32.reset_inactivity()
        self.backlight_timer.after(10, self.BacklightOn)

    def GainFocus(self, has_focus):
        if has_focus:
            self.backlight_timer.after(10, self.BacklightOn)
        else:
            self.backlight_timer.cancel()

    def ShowRecentFiles(self):
        books = self.doc_info.GetLibrary()
        self.env = EnvironmentSaver()
        #print books
        #return None
        #app.exit_key_handler = self.destroy
        app.menu = [(u'Open', self.RecentFilesCB), (u'Close', self.RecentFilesClose)]
        app.screen='normal'
        app.body = Listbox(books, self.RecentFilesCB)
        app.exit_key_handler = self.RecentFilesClose
        self.recent_lb_lock = e32.Ao_lock()
        self.recent_lb_lock.wait()

    def RecentFilesClose(self):
        self.env.Restore()
        self.recent_lb_lock.signal()

    def RecentFilesCB(self, ind=None):
        if ind == None:
            ind = app.body.current()
        self.RecentFilesClose()
        self.OpenFilename(self.doc_info.GetLibrary()[ind][0])
        print self.doc_info.GetLibrary()[ind][0]
        self.RedrawCB(None)
        return None

    def OpenFilename(self, filename):
        if self.doc:
            self.doc_info.SetLastPos(self.doc.filename, self.doc.GetPos())
            self.doc.Close()

        self.doc = Document(filename, self.config)
        self.doc.SetPos(self.doc_info.GetLastPos(filename))
        self.prev_file_pos = self.doc.GetPos()
        self.prev_event_get_next = True
        self.prev_event_get_prev = False
        self.doc_info.last_file = filename
        self.txt = self.doc.GetNextNLines(self.get_max_number_of_lines(), self.get_max_line_width())

    def OpenFile(self):
        browser = FileBrowser()
        #browser.SetDir("e:\\eBooks")
        browser.run()
        if not browser.success:
            return None
        self.OpenFilename(browser.filename)
        self.RedrawCB(None)

    def GoToStartOfFile(self):
        if self.doc == None:
            return None
        self.doc.SetPos(0)
        self.txt = self.doc.GetNextNLines(self.get_max_number_of_lines(), self.get_max_line_width())
        self.RedrawCB(None)

    def Quit(self):
        if self.doc != None:
            self.doc_info.SetLastPos(self.doc.filename, self.doc.GetPos())
            self.doc_info.Save()
        self.backlight_timer.cancel()
        self.app_lock.signal()

    def get_max_number_of_lines(self):
        return (app.body.size[1] - self.config.offset[1] - self.config.offset[3]) / self.config.line_spacing;

    def get_max_line_width(self):
        return app.body.size[0] - self.config.offset[0] - self.config.offset[2];

    def draw_text_normal(self, text, row):
        #
        #if text.find("<strong>") >= 0:
        #    flags |= FONT_BOLD
        #if text.find("</strong>") >= 0:
        #    flags &= ~FONT_BOLD
        #print flags
        '''
        if text.find("<emphasis>") >= 0:
            flags |= FONT_ITALIC
        if text.find("</emphasis>") >=0:
            flags &= ~FONT_ITALIC

        format_map = create_format_map(text) #TODO sort
        if len(format_map) > 0:
            # text has formating tags
            flags = 0
            total_width = config.offset[0]
            for f in format_map:
                print text[:f[0]]
                app.body.text([total_width, config.offset[1] + config.line_spacing*row+config.line_spacing],
                              strip_text(text[:f[0]]),
                              config.GetColor(config.font_color),
                              (config.font, config.font_size, FO))
                total_width += app.body.measure_text(strip_text(text[:f[0]]), (config.font, config.font_size, flags))[0][2]
                flags = f[1]

        else:
        '''
        # strong, emphasis, strikethrough, code
        app.body.text([self.config.offset[0], self.config.offset[1] + self.config.line_spacing*row + self.config.line_spacing],
                      strip_text(text),
                      self.config.GetColor(self.config.font_color),
                      (self.config.font, self.config.font_size, FONT_ANTIALIAS))


    def draw_text(self, rect=None):
        if not rect:
            app.body.begin_redraw()
            #print "can redraw"
        app.body.clear(self.config.GetColor(self.config.background_color))
        row = 0
        for l in self.txt:
            self.draw_text_normal(l, row)
            row += 1
        # draw rectangle below status line:
        rect_width = 30
        if self.doc != None:
            offset = int(self.doc.GetRelativePos()/100.0 * (app.body.size[0]-rect_width))
            app.body.rectangle([0+offset, app.body.size[1]-10, rect_width+offset, app.body.size[1]], fill=0x505050)
            # status line:

            app.body.text([0, app.body.size[1]],
                          unicode(self.doc.GetRelativePos())+u'%',
                          self.config.GetColor(self.config.status_font_color),
                          (self.config.status_font, self.config.status_font_size, FONT_ANTIALIAS))

            dims = app.body.measure_text(unicode(self.doc.GetRelativePos())+u'%',
                                  (self.config.status_font, self.config.status_font_size, FONT_ANTIALIAS))
            app.body.text([dims[1]+20, app.body.size[1]],
                          unicode(self.doc.filename),
                          self.config.GetColor(self.config.status_font_color),
                          (self.config.status_font, self.config.status_font_size, FONT_ANTIALIAS))
        if not rect:
            app.body.end_redraw()

    def RedrawCB(self, rect=None):
        if rect != None:
            #orientation changed?
            self.doc.SetPos(self.prev_file_pos)
            self.txt = self.doc.GetNextNLines(self.get_max_number_of_lines(), self.get_max_line_width())
            self.prev_event_get_prev = False
            self.prev_event_get_next = True
        self.draw_text(rect)

    def EventCB(self, event):
        if self.doc == None:
            return None
        if event['type'] == key_codes.EDrag:
            #print "DRAG", event['pos']
            rect_width = 30
            if event['pos'][1] > (app.body.size[1] - 20 ):
                new_pos = int(float(event['pos'][0]-rect_width/2) / (app.body.size[0]-rect_width) * self.doc.filesize)
                if new_pos < 0:
                    new_pos = 0
                self.doc.SetPos(new_pos)
                self.prev_file_pos = new_pos
                self.prev_event_get_prev = False
                self.prev_event_get_next = True
                self.txt = self.doc.GetNextNLines(self.get_max_number_of_lines(), self.get_max_line_width())
            self.RedrawCB(None)

        elif event['type'] == key_codes.EButton1Down:
            if event['pos'][1] > (app.body.size[1] - 30 ):
                # bottom bar
                new_pos = int(float(event['pos'][0]) / app.body.size[0] * self.doc.filesize)
                self.prev_file_pos = new_pos
                self.prev_event_get_prev = False
                self.prev_event_get_next = True
                self.doc.SetPos(new_pos)
                self.txt = self.doc.GetNextNLines(self.get_max_number_of_lines(), self.get_max_line_width())
            elif event['pos'][1] > (app.body.size[1] / 3*2):
                # lower 1/3
                if self.prev_event_get_prev:
                    self.doc.SetPos(self.prev_file_pos)
                    self.prev_event_get_prev = False
                    #self.txt = self.doc.GetNextNLines(self.get_max_number_of_lines(), self.get_max_line_width())
                self.prev_file_pos = self.doc.GetPos()
                self.txt = self.doc.GetNextNLines(self.get_max_number_of_lines(), self.get_max_line_width())

                self.prev_event_get_next = True
                # upper 1/3
            elif event['pos'][1] < (app.body.size[1] / 3):
                if self.prev_event_get_next:
                    self.doc.SetPos(self.prev_file_pos)
                    self.prev_event_get_next = False
                    #self.txt = self.doc.GetPrevNLines(self.get_max_number_of_lines(), self.get_max_line_width())
                self.prev_file_pos = self.doc.GetPos()
                self.txt = self.doc.GetPrevNLines(self.get_max_number_of_lines(), self.get_max_line_width())
                self.prev_event_get_prev = True
            else:
                # in the middle, toggle menu
                if app.screen == 'large':
                    app.screen = 'full'
                else:
                    app.screen = 'large'
                if self.prev_event_get_prev == False:
                    self.doc.SetPos(self.prev_file_pos)
                self.prev_event_get_prev = False
                self.prev_event_get_next = True
                self.txt = self.doc.GetNextNLines(self.get_max_number_of_lines(), self.get_max_line_width())
            self.RedrawCB(None)

'''
def draw_text_justified(text, row):
    global config
    if text.find('\n') >= 0:
        app.body.text([config.offset[0], config.offset[1] + config.line_spacing*row+config.line_spacing],
                      strip_text(text),
                      config.GetColor(config.font_color),
                      (config.font, config.font_size, FONT_ANTIALIAS))
        return None
    text = strip_text(text)
    words = string.split(text, ' ')
    widths = []
    totalwidth = 0
    for w in words:
        word_width = app.body.measure_text(w, (config.font, config.font_size, FONT_ANTIALIAS))[0][2]
        widths.append(word_width)
        totalwidth += word_width
    space_size = (get_max_line_width() - totalwidth) / (len(words)-1)


    app.body.text([config.offset[0], config.offset[1] + config.line_spacing*row+config.line_spacing],
                  words[0],
                  config.GetColor(config.font_color),
                  (config.font, config.font_size, FONT_ANTIALIAS))
    prev_word_total_width = widths[0] + space_size + config.offset[0]
    for i in range(1, len(words)):
        app.body.text([prev_word_total_width, config.offset[1] + config.line_spacing*row+config.line_spacing],
                      words[i],
                      config.GetColor(config.font_color),
                      (config.font, config.font_size, FONT_ANTIALIAS))
        prev_word_total_width += widths[i] + space_size
'''
re_tag = re.compile('<.*>')
re_tag2 = re.compile('[ ][ ]+')

application = Application()
application.Run()