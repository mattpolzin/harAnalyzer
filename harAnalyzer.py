#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys, string, os, json, re
from curses import setupterm, tigetstr, tigetnum, tparm
if os.name == 'nt': import ctypes, struct



# force utf-8 encoding
reload(sys)
sys.setdefaultencoding('utf-8')

if os.name == 'nt': import uniconsole



# tty colors
DEFAULT = '\x1b[39m'
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, LIGHT_GREY = [('\x1b[%dm' % (30 + i)) for i in range(8)]
GREY, BRIGHT_RED, BRIGHT_GREEN, BRIGHT_YELLOW, BRIGHT_BLUE, BRIGHT_MAGENTA, BRIGHT_CYAN, WHITE = [('\x1b[%dm' % (90 + i)) for i in range(8)]
RESET, NORMAL, BOLD, DIM, UNDERLINE, INVERT, HIDDEN = [('\x1b[%dm' % i) for i in (0, 22, 1, 2, 4, 7, 8)]
ATTRS = {
    'DEFAULT': DEFAULT,
    'BLACK': BLACK, 'RED': RED, 'GREEN': GREEN, 'YELLOW': YELLOW, 'BLUE': BLUE, 'MAGENTA': MAGENTA, 'CYAN': CYAN, 'LIGHT_GREY': LIGHT_GREY,
    'GREY': GREY, 'BRIGHT_RED': BRIGHT_RED, 'BRIGHT_GREEN': BRIGHT_GREEN, 'BRIGHT_YELLOW': BRIGHT_YELLOW, 'BRIGHT_BLUE': BRIGHT_BLUE, 'BRIGHT_MAGENTA': BRIGHT_MAGENTA, 'BRIGHT_CYAN': BRIGHT_CYAN, 'WHITE': WHITE,
    'RESET': RESET, 'NORMAL': NORMAL, 'BOLD': BOLD, 'DIM': DIM, 'UNDERLINE': UNDERLINE, 'INVERT': INVERT, 'HIDDEN': HIDDEN
}



resource_columns = [
    {
        'title': 'Total time',
        'width': 12,
        'path': 'time',
        'threshold': 10000
    },
    {
        'title': 'Blocked',
        'width': 9,
        'path': 'timings/blocked',
        'threshold': 500
    },
    {
        'title': 'DNS',
        'width': 9,
        'path': 'timings/dns',
        'threshold': 500
    },
    {
        'title': 'Connect',
        'width': 9,
        'path': 'timings/connect',
        'threshold': 500
    },
    {
        'title': 'Send',
        'width': 9,
        'path': 'timings/send',
        'threshold': 1000
    },
    {
        'title': 'Wait',
        'width': 9,
        'path': 'timings/wait',
        'threshold': 2000
    },
    {
        'title': 'Receive',
        'width': 9,
        'path': 'timings/receive',
        'threshold': 500
    },
    {
        'title': 'SSL',
        'width': 9,
        'path': 'timings/ssl',
        'threshold': 100
    }
]


columns = reduce(lambda x, y: x + y['width'], resource_columns, 0)
has_color = False
is_tty = False



def indentPrint(i_str, indentation=0, newline=False):
    p_str =  '  ' * indentation
    p_str += str(i_str)
    if newline:
        p_str += '\n'
    cprint(p_str, trim=False)


def itemAtPath(resource, path):
    if type(path) == str:
        return itemAtPath(resource, path.split('/'))
    if len(path) == 0:
        return resource
    return itemAtPath(resource[path[0]], path[1:])


def resourceString(resource=None):
    ret = ''
    print_titles = True if not resource else False
    for column in resource_columns:
        if print_titles:
            ret += '%*s' % (column['width'], column['title'])
        else:
            item = itemAtPath(resource, column['path'])
            if column['threshold']:
                if int(item) > column['threshold']:
                    ret += "${RED}"
                else:
                    ret += "${GREEN}"
            ret += '%*s' % (column['width'], str(item))
            ret += "${RESET}"
    return ret


def timeBar(amt, max_amt, width=12):
    return '#' * int((width * amt) / max_amt)


def trim(raw, width):
    # TODO: >>> This could probably be much simpler if I was smarter
    seq = ''
    str_len = 0
    i = 0
    matchiter = re.finditer(r'(\x1b.*?m)', raw.strip())
    for match in matchiter:
        chunk = raw[i:match.start()]
        i = match.end()
        if str_len + len(chunk) > width:
            chunk = chunk[0:width - str_len - 1] + u'\u2026'
        str_len = str_len + len(chunk)
        seq = seq + chunk + match.group()

        if (str_len >= width):
            break

    if str_len < width:
        chunk = raw[i:]
        if str_len + len(chunk) > width:
            chunk = chunk[0:width - str_len - 1] + u'\u2026'
        seq = seq + chunk

    return seq


def elipsify(seq):
    return seq[0:-1].strip(string.punctuation) + u'\u2026'


def cprint(str, attr=None, trim=True, width=columns):
    sys.__stdout__.write(render(str, attr, trim, width) + '\r\n')


def _render_sub(match):
    s = match.group()
    if s == '$$':
        return s
    else:
        return ATTRS.get(s[2:-1], '')


def render(str, attr=None, trim_string=True, width=columns):
    if has_color:
        if attr:
            if isinstance(attr, list):
                attr = ''.join(attr)
        else:
            attr = ''

        seq = re.sub(r'\$\$|\${\w+}', _render_sub, str)
        if trim_string:
            seq = trim(seq, width)

        return attr + seq + RESET
    else:
        seq = re.sub(r'\$\$|\${\w+}', '', str)
        if trim_string and len(seq) > width:
            return seq[0:columns - 1] + u'\u2026'
        return seq


def _get_terminal_size_windows():
    try:
        from ctypes import windll, create_string_buffer
        # stdin handle is -10
        # stdout handle is -11
        # stderr handle is -12
        h = windll.kernel32.GetStdHandle(-12)
        csbi = create_string_buffer(22)
        res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
        if res:
            (bufx, bufy, curx, cury, wattr,
            left, top, right, bottom,
            maxx, maxy) = struct.unpack("hhhhHhhhhhh", csbi.raw)
            sizex = right - left + 1
            sizey = bottom - top + 1
            return sizex, sizey
    except:
        pass


if hasattr(sys.__stdout__, "isatty") and sys.__stdout__.isatty():
    try:
        if os.name != 'nt': 
            setupterm()
            has_color = (tigetnum('colors') > 2)
            columns = min(columns, tigetnum('cols'))
        else:
            has_color = True
            columns = min(columns, _get_terminal_size_windows()[0] - 1)
        
        is_tty = True
    except:
        pass
else:
    try:
        (_, tcols) = os.popen('stty size', 'r').read().split()
        columns = int(min(columns, tcols))
    except:
        pass


har_file = open(sys.argv[1], 'r')
har_tree = json.loads(har_file.read())

hide_urls = len(sys.argv) > 2 and '-u' in sys.argv
show_details = len(sys.argv) > 2 and '-i' in sys.argv
if show_details:
    arg_idx = sys.argv.index('-i')
    try:
        details_id = int(sys.argv[arg_idx+1])
    except:
        details_id = -1

pages = {}
for page in har_tree['log']['pages']:
    page['resources'] = []
    pages[page['id']] = page

har_tree['log']['entries'].sort(key=lambda x: x['time'], reverse=True)

for resource in har_tree['log']['entries']:
    pageRef = resource['pageref']
    if pages[pageRef]:
        pages[pageRef]['resources'].append(resource)
    else:
        print "Found resource w/o page: " + str(resource) + "\n"

for page_key in pages:
    page = pages[page_key]
    indentPrint(page['title'])
    if len(page['resources']) > 0:
        if show_details and details_id != -1:
            resource = page['resources'][details_id]
            print json.dumps(resource, indent=4, sort_keys=True)
        else:
            max_time = page['resources'][0]['time']
            indentPrint('    ' + resourceString(), 2)
            idx = 0
            for resource in page['resources']:
                if not hide_urls:
                    indentPrint(trim(resource['request']['url'], columns - 16) +
                        ' (status: ' + str(resource['response']['status']) + ')', 1)
                indentPrint("%4d" % idx + resourceString(resource) + '\t' +
                    timeBar(resource['time'], max_time, 25), 2)
                idx += 1
    else:
        print "No resources for page..."
