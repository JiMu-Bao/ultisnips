#!/usr/bin/env python
# encoding: utf-8
#
# To execute this test requires two terminals, one for running Vim and one
# for executing the test script.  Both terminals should have their current
# working directories set to this directory (the one containing this test.py
# script).
#
# In one terminal, launch a GNU ``screen`` session named ``vim``:
#   $ screen -S vim
#
# Within this new session, launch Vim with the absolute bare minimum settings
# to ensure a consistent test environment:
#  $ vim -u NONE
#
# The '-u NONE' disables normal .vimrc and .gvimrc processing (note
# that '-u NONE' implies '-U NONE').
#
# All other settings are configured by the test script.
#
# Now, from another terminal, launch the testsuite:
#    $ ./test.py
# 
# The testsuite will use ``screen`` to inject commands into the Vim under test,
# and will compare the resulting output to expected results.

import os
import tempfile
import unittest
import time
from textwrap import dedent

# Some constants for better reading
BS = '\x7f'
ESC = '\x1b'
ARR_L = '\x1bOD'
ARR_R = '\x1bOC'
ARR_U = '\x1bOA'
ARR_D = '\x1bOB'

# Defined Constants
JF = "?" # Jump forwards
JB = "+" # Jump backwards
LS = "@" # List snippets
EX = "\t" # EXPAND

# Some VIM functions
COMPL_KW = chr(24)+chr(14)
COMPL_ACCEPT = chr(25)

def send(s,session):
    s = s.replace("'", r"'\''")
    os.system("screen -x %s -X stuff '%s'" % (session, s))

def type(str, session, sleeptime):
    """
    Send the keystrokes to vim via screen. Pause after each char, so
    vim can handle this
    """
    for c in str:
        send(c, session)
        time.sleep(sleeptime)

class _VimTest(unittest.TestCase):
    snippets = ("dummy", "donotdefine")
    snippets_test_file = ("", "", "")  # file type, file name, file content
    text_before = " --- some text before --- "
    text_after =  " --- some text after --- "
    expected_error = ""
    wanted = ""
    keys = ""
    sleeptime = 0.00

    def send(self,s):
        send(s, self.session)

    def send_py(self,s):
        self.send(":py << EOF\n%s\nEOF\n" % s)

    def type(self,s):
        type(s, self.session, self.sleeptime)

    def check_output(self):
        wanted = self.text_before + '\n\n' + self.wanted + \
                '\n\n' + self.text_after
        if self.expected_error:
            wanted = wanted + "\n" + self.expected_error
        for i in range(4):
            if self.output != wanted:
                self.setUp()
        self.assertEqual(self.output, wanted)

    def runTest(self): self.check_output()

    def _options_on(self):
        pass

    def _options_off(self):
        pass

    def setUp(self):
        self.send(ESC)

        self.send(":py UltiSnips_Manager.reset(test_error=True)\n")

        # Clear the buffer
        self.send("bggVGd")

        if not isinstance(self.snippets[0],tuple):
            self.snippets = ( self.snippets, )

        for s in self.snippets:
            sv,content = s[:2]
            descr = ""
            options = ""
            if len(s) > 2:
                descr = s[2]
            if len(s) > 3:
                options = s[3]

            self.send_py("UltiSnips_Manager.add_snippet(%r, %r, %r, %r)" %
                (sv, content, descr, options))

        ft, fn, file_data = self.snippets_test_file
        if ft:
            self.send_py("UltiSnips_Manager._parse_snippets(%r, %r, %r)" %
                (ft, fn, dedent(file_data + '\n')))

        if not self.interrupt:
            # Enter insert mode
            self.send("i")

            self.send(self.text_before + '\n\n')
            self.send('\n\n' + self.text_after)

            self.send(ESC)

            # Go to the middle of the buffer
            self.send(ESC + "ggjj")

            self._options_on()

            self.send("i")

            # Execute the command
            self.type(self.keys)

            self.send(ESC)

            self._options_off()

            handle, fn = tempfile.mkstemp(prefix="UltiSnips_Test",suffix=".txt")
            os.close(handle)
            os.unlink(fn)

            self.send(ESC + ":w! %s\n" % fn)

            # Read the output, chop the trailing newline
            tries = 50
            while tries:
                if os.path.exists(fn):
                    self.output = open(fn,"r").read()[:-1]
                    break
                time.sleep(.05)
                tries -= 1

##################
# Simple Expands #
##################
class _SimpleExpands(_VimTest):
    snippets = ("hallo", "Hallo Welt!")

class SimpleExpand_ExceptCorrectResult(_SimpleExpands):
    keys = "hallo" + EX
    wanted = "Hallo Welt!"
class SimpleExpandTwice_ExceptCorrectResult(_SimpleExpands):
    keys = "hallo" + EX + '\nhallo' + EX
    wanted = "Hallo Welt!\nHallo Welt!"

class SimpleExpandNewLineAndBackspae_ExceptCorrectResult(_SimpleExpands):
    keys = "hallo" + EX + "\nHallo Welt!\n\n\b\b\b\b\b"
    wanted = "Hallo Welt!\nHallo We"
    def _options_on(self):
        self.send(":set backspace=eol,start\n")
    def _options_off(self):
        self.send(":set backspace=\n")

class SimpleExpandTypeAfterExpand_ExceptCorrectResult(_SimpleExpands):
    keys = "hallo" + EX + "and again"
    wanted = "Hallo Welt!and again"

class SimpleExpandTypeAndDelete_ExceptCorrectResult(_SimpleExpands):
    keys = "na du hallo" + EX + "and again\b\b\b\b\bblub"
    wanted = "na du Hallo Welt!and blub"

class DoNotExpandAfterSpace_ExceptCorrectResult(_SimpleExpands):
    keys = "hallo " + EX
    wanted = "hallo " + EX

class ExitSnippetModeAfterTabstopZero(_VimTest):
    snippets = ("test", "SimpleText")
    keys = "test" + EX + EX
    wanted = "SimpleText" + EX

class ExpandInTheMiddleOfLine_ExceptCorrectResult(_SimpleExpands):
    keys = "Wie hallo gehts" + ESC + "bhi" + EX
    wanted = "Wie Hallo Welt! gehts"
class MultilineExpand_ExceptCorrectResult(_VimTest):
    snippets = ("hallo", "Hallo Welt!\nUnd Wie gehts")
    keys = "Wie hallo gehts" + ESC + "bhi" + EX
    wanted = "Wie Hallo Welt!\nUnd Wie gehts gehts"
class MultilineExpandTestTyping_ExceptCorrectResult(_VimTest):
    snippets = ("hallo", "Hallo Welt!\nUnd Wie gehts")
    wanted = "Wie Hallo Welt!\nUnd Wie gehtsHuiui! gehts"
    keys = "Wie hallo gehts" + ESC + "bhi" + EX + "Huiui!"

class MultilineExpandWithFormatoptionsOn_ExceptCorrectResult(_VimTest):
    snippets = ("test", "${1:longer expand}\n$0")
    keys = "test" + EX + "This is a longer text that should wrap"
    wanted = "This is a longer\ntext that should\nwrap\n"
    def _options_on(self):
        self.send(":set tw=20\n")
    def _options_off(self):
        self.send(":set tw=0\n")


############
# TabStops #
############
class TabStopSimpleReplace_ExceptCorrectResult(_VimTest):
    snippets = ("hallo", "hallo ${0:End} ${1:Beginning}")
    keys = "hallo" + EX + "na" + JF + "Du Nase"
    wanted = "hallo Du Nase na"
class TabStopSimpleReplaceSurrounded_ExceptCorrectResult(_VimTest):
    snippets = ("hallo", "hallo ${0:End} a small feed")
    keys = "hallo" + EX + "Nase"
    wanted = "hallo Nase a small feed"
class TabStopSimpleReplaceSurrounded1_ExceptCorrectResult(_VimTest):
    snippets = ("hallo", "hallo $0 a small feed")
    keys = "hallo" + EX + "Nase"
    wanted = "hallo Nase a small feed"
class TabStopSimpleReplaceEndingWithNewline_ExceptCorrectResult(_VimTest):
    snippets = ("hallo", "Hallo Welt\n")
    keys = "hallo" + EX + "\nAnd more"
    wanted = "Hallo Welt\n\nAnd more"


class ExitTabStop_ExceptCorrectResult(_VimTest):
    snippets = ("echo", "$0 run")
    keys = "echo" + EX + "test"
    wanted = "test run"

class TabStopNoReplace_ExceptCorrectResult(_VimTest):
    snippets = ("echo", "echo ${1:Hallo}")
    keys = "echo" + EX
    wanted = "echo Hallo"

class TabStop_EscapingCharsBackticks(_VimTest):
    snippets = ("test", r"snip \` literal")
    keys = "test" + EX
    wanted = "snip ` literal"
class TabStop_EscapingCharsDollars(_VimTest):
    snippets = ("test", r"snip \$0 $$0 end")
    keys = "test" + EX + "hi"
    wanted = "snip $0 $hi end"
class TabStop_EscapingChars_RealLife(_VimTest):
    snippets = ("test", r"usage: \`basename \$0\` ${1:args}")
    keys = "test" + EX + "[ -u -v -d ]"
    wanted = "usage: `basename $0` [ -u -v -d ]"

class TabStopEscapingWhenSelected_ECR(_VimTest):
    snippets = ("test", "snip ${1:default}")
    keys = "test" + EX + ESC + "0ihi"
    wanted = "hisnip default"
class TabStopEscapingWhenSelectedSingleCharTS_ECR(_VimTest):
    snippets = ("test", "snip ${1:i}")
    keys = "test" + EX + ESC + "0ihi"
    wanted = "hisnip i"
class TabStopEscapingWhenSelectedNoCharTS_ECR(_VimTest):
    snippets = ("test", "snip $1")
    keys = "test" + EX + ESC + "0ihi"
    wanted = "hisnip "

class TabStopUsingBackspaceToDeleteDefaultValue_ECR(_VimTest):
    snippets = ("test", "snip ${1/.+/(?0:matched)/} ${1:default}")
    keys = "test" + EX + BS
    wanted = "snip  "
class TabStopUsingBackspaceToDeleteDefaultValueInFirstTab_ECR(_VimTest):
    sleeptime = 0.09 # Do this very slowly
    snippets = ("test", "snip ${1/.+/(?0:m1)/} ${2/.+/(?0:m2)/} "
                "${1:default} ${2:def}")
    keys = "test" + EX + BS + JF + "hi"
    wanted = "snip  m2  hi"
class TabStopUsingBackspaceToDeleteDefaultValueInSecondTab_ECR(_VimTest):
    snippets = ("test", "snip ${1/.+/(?0:m1)/} ${2/.+/(?0:m2)/} "
                "${1:default} ${2:def}")
    keys = "test" + EX + "hi" + JF + BS
    wanted = "snip m1  hi "
class TabStopUsingBackspaceToDeleteDefaultValueTypeSomethingThen_ECR(_VimTest):
    snippets = ("test", "snip ${1/.+/(?0:matched)/} ${1:default}")
    keys = "test" + EX + BS + "hallo"
    wanted = "snip matched hallo"

class TabStopWithOneChar_ExceptCorrectResult(_VimTest):
    snippets = ("hallo", "nothing ${1:i} hups")
    keys = "hallo" + EX + "ship"
    wanted = "nothing ship hups"

class TabStopTestJumping_ExceptCorrectResult(_VimTest):
    snippets = ("hallo", "hallo ${2:End} mitte ${1:Beginning}")
    keys = "hallo" + EX + JF + "Test" + JF + "Hi"
    wanted = "hallo Test mitte BeginningHi"
class TabStopTestJumping2_ExceptCorrectResult(_VimTest):
    snippets = ("hallo", "hallo $2 $1")
    keys = "hallo" + EX + JF + "Test" + JF + "Hi"
    wanted = "hallo Test Hi"
class TabStopTestJumpingRLExampleWithZeroTab_ExceptCorrectResult(_VimTest):
    snippets = ("test", "each_byte { |${1:byte}| $0 }")
    keys = "test" + EX + JF + "Blah"
    wanted = "each_byte { |byte| Blah }"

class TestJumpingDontJumpToEndIfThereIsTabZero_ExceptCorrectResult(_VimTest):
    snippets = ("hallo", "hallo $0 $1")
    keys = "hallo" + EX + "Test" + JF + "Hi" + JF + JF + "du"
    wanted = "hallo Hidu Test"

class TabStopTestBackwardJumping_ExceptCorrectResult(_VimTest):
    snippets = ("hallo", "hallo ${2:End} mitte${1:Beginning}")
    keys = "hallo" + EX + "Somelengthy Text" + JF + "Hi" + JB + \
            "Lets replace it again" + JF + "Blah" + JF + JB*2 + JF
    wanted = "hallo Blah mitteLets replace it again"
class TabStopTestBackwardJumping2_ExceptCorrectResult(_VimTest):
    snippets = ("hallo", "hallo $2 $1")
    keys = "hallo" + EX + "Somelengthy Text" + JF + "Hi" + JB + \
            "Lets replace it again" + JF + "Blah" + JF + JB*2 + JF
    wanted = "hallo Blah Lets replace it again"

class TabStopTestMultilineExpand_ExceptCorrectResult(_VimTest):
    snippets = ("hallo", "hallo $0\nnice $1 work\n$3 $2\nSeem to work")
    keys ="test hallo World" + ESC + "02f i" + EX + "world" + JF + "try" + \
            JF + "test" + JF + "one more" + JF + JF
    wanted = "test hallo one more\nnice world work\n" \
            "test try\nSeem to work World"

class TabStop_TSInDefaultTextRLExample_OverwriteNone_ECR(_VimTest):
    snippets = ("test", """<div${1: id="${2:some_id}"}>\n  $0\n</div>""")
    keys = "test" + EX
    wanted = """<div id="some_id">\n  \n</div>"""
class TabStop_TSInDefaultTextRLExample_OverwriteFirst(_VimTest):
    snippets = ("test", """<div${1: id="${2:some_id}"}>\n  $0\n</div>""")
    keys = "test" + EX + " blah" + JF + "Hallo"
    wanted = """<div blah>\n  Hallo\n</div>"""
class TabStop_TSInDefaultTextRLExample_DeleteFirst(_VimTest):
    snippets = ("test", """<div${1: id="${2:some_id}"}>\n  $0\n</div>""")
    keys = "test" + EX + BS + JF + "Hallo"
    wanted = """<div>\n  Hallo\n</div>"""
class TabStop_TSInDefaultTextRLExample_OverwriteFirstJumpBack(_VimTest):
    snippets = ("test", """<div${1: id="${2:some_id}"}>\n  $3  $0\n</div>""")
    keys = "test" + EX + "Hi" + JF + "Hallo" + JB + "SomethingElse" + JF + \
            "Nupl" + JF + "Nox"
    wanted = """<divSomethingElse>\n  Nupl  Nox\n</div>"""
class TabStop_TSInDefaultTextRLExample_OverwriteSecond(_VimTest):
    snippets = ("test", """<div${1: id="${2:some_id}"}>\n  $0\n</div>""")
    keys = "test" + EX + JF + "no" + JF + "End"
    wanted = """<div id="no">\n  End\n</div>"""
class TabStop_TSInDefaultTextRLExample_OverwriteSecondTabBack(_VimTest):
    snippets = ("test", """<div${1: id="${2:some_id}"}>\n  $3 $0\n</div>""")
    keys = "test" + EX + JF + "no" + JF + "End" + JB + "yes" + JF + "Begin" \
            + JF + "Hi"
    wanted = """<div id="yes">\n  Begin Hi\n</div>"""
class TabStop_TSInDefaultTextRLExample_OverwriteSecondTabBackTwice(_VimTest):
    snippets = ("test", """<div${1: id="${2:some_id}"}>\n  $3 $0\n</div>""")
    keys = "test" + EX + JF + "no" + JF + "End" + JB + "yes" + JB + \
            " allaway" + JF + "Third" + JF + "Last"
    wanted = """<div allaway>\n  Third Last\n</div>"""

class TabStop_TSInDefaultNested_OverwriteOneJumpBackToOther(_VimTest):
    snippets = ("test", "hi ${1:this ${2:second ${3:third}}} $4")
    keys = "test" + EX + JF + "Hallo" + JF + "Ende"
    wanted = "hi this Hallo Ende"
class TabStop_TSInDefaultNested_OverwriteOneJumpToThird(_VimTest):
    snippets = ("test", "hi ${1:this ${2:second ${3:third}}} $4")
    keys = "test" + EX + JF + JF + "Hallo" + JF + "Ende"
    wanted = "hi this second Hallo Ende"
class TabStop_TSInDefaultNested_OverwriteOneJumpAround(_VimTest):
    snippets = ("test", "hi ${1:this ${2:second ${3:third}}} $4")
    keys = "test" + EX + JF + JF + "Hallo" + JB+JB + "Blah" + JF + "Ende"
    wanted = "hi Blah Ende"

class TabStop_TSInDefault_MirrorsOutside_DoNothing(_VimTest):
    snippets = ("test", "hi ${1:this ${2:second}} $2")
    keys = "test" + EX
    wanted = "hi this second second"
class TabStop_TSInDefault_MirrorsOutside_OverwriteSecond(_VimTest):
    snippets = ("test", "hi ${1:this ${2:second}} $2")
    keys = "test" + EX + JF + "Hallo"
    wanted = "hi this Hallo Hallo"
class TabStop_TSInDefault_MirrorsOutside_Overwrite(_VimTest):
    snippets = ("test", "hi ${1:this ${2:second}} $2")
    keys = "test" + EX + "Hallo"
    wanted = "hi Hallo "

class TabStop_Multiline_Leave(_VimTest):
    snippets = ("test", "hi ${1:first line\nsecond line} world" )
    keys = "test" + EX
    wanted = "hi first line\nsecond line world"
class TabStop_Multiline_Overwrite(_VimTest):
    snippets = ("test", "hi ${1:first line\nsecond line} world" )
    keys = "test" + EX + "Nothing"
    wanted = "hi Nothing world"
class TabStop_Multiline_MirrorInFront_Leave(_VimTest):
    snippets = ("test", "hi $1 ${1:first line\nsecond line} world" )
    keys = "test" + EX
    wanted = "hi first line\nsecond line first line\nsecond line world"
class TabStop_Multiline_MirrorInFront_Overwrite(_VimTest):
    snippets = ("test", "hi $1 ${1:first line\nsecond line} world" )
    keys = "test" + EX + "Nothing"
    wanted = "hi Nothing Nothing world"
class TabStop_Multiline_DelFirstOverwriteSecond_Overwrite(_VimTest):
    snippets = ("test", "hi $1 $2 ${1:first line\nsecond line} ${2:Hi} world" )
    keys = "test" + EX + BS + JF + "Nothing"
    wanted = "hi  Nothing  Nothing world"

###########################
# ShellCode Interpolation #
###########################
class TabStop_Shell_SimpleExample(_VimTest):
    snippets = ("test", "hi `echo hallo` you!")
    keys = "test" + EX + "and more"
    wanted = "hi hallo you!and more"
class TabStop_Shell_TextInNextLine(_VimTest):
    snippets = ("test", "hi `echo hallo`\nWeiter")
    keys = "test" + EX + "and more"
    wanted = "hi hallo\nWeiterand more"
class TabStop_Shell_InDefValue_Leave(_VimTest):
    sleeptime = 0.09 # Do this very slowly
    snippets = ("test", "Hallo ${1:now `echo fromecho`} end")
    keys = "test" + EX + JF + "and more"
    wanted = "Hallo now fromecho endand more"
class TabStop_Shell_InDefValue_Overwrite(_VimTest):
    snippets = ("test", "Hallo ${1:now `echo fromecho`} end")
    keys = "test" + EX + "overwrite" + JF + "and more"
    wanted = "Hallo overwrite endand more"
class TabStop_Shell_TestEscapedChars_Overwrite(_VimTest):
    snippets = ("test", r"""`echo \`echo "\\$hi"\``""")
    keys = "test" + EX
    wanted = "$hi"
class TabStop_Shell_TestEscapedCharsAndShellVars_Overwrite(_VimTest):
    snippets = ("test", r"""`hi="blah"; echo \`echo "$hi"\``""")
    keys = "test" + EX
    wanted = "blah"

class TabStop_Shell_ShebangPython(_VimTest):
    sleeptime = 0.09 # Do this very slowly
    snippets = ("test", """Hallo ${1:now `#!/usr/bin/env python
print "Hallo Welt"
`} end""")
    keys = "test" + EX + JF + "and more"
    wanted = "Hallo now Hallo Welt endand more"

############################
# PythonCode Interpolation #
############################

#### Deprecated way ##########
class PythonCodeOld_SimpleExample(_VimTest):
    snippets = ("test", """hi `!p res = "Hallo"` End""")
    keys = "test" + EX
    wanted = "hi Hallo End"
class PythonCodeOld_ReferencePlaceholder(_VimTest):
    snippets = ("test", """${1:hi} `!p res = t[1]+".blah"` End""")
    keys = "test" + EX + "ho"
    wanted = "ho ho.blah End"
class PythonCodeOld_ReferencePlaceholderBefore(_VimTest):
    snippets = ("test", """`!p res = len(t[1])*"#"`\n${1:some text}""")
    keys = "test" + EX + "Hallo Welt"
    wanted = "##########\nHallo Welt"
class PythonCodeOld_TransformedBeforeMultiLine(_VimTest):
    snippets = ("test", """${1/.+/egal/m} ${1:`!p
res = "Hallo"`} End""")
    keys = "test" + EX
    wanted = "egal Hallo End"
class PythonCodeOld_IndentedMultiline(_VimTest):
    snippets = ("test", """start `!p a = 1
b = 2
if b > a:
    res = "b isbigger a"
else:
    res = "a isbigger b"` end""")
    keys = "    test" + EX
    wanted = "    start b isbigger a end"

#### New way ##########

class PythonCode_UseNewOverOld(_VimTest):
    snippets = ("test", """hi `!p res = "Old"
snip.rv = "New"` End""")
    keys = "test" + EX
    wanted = "hi New End"

class PythonCode_SimpleExample(_VimTest):
    snippets = ("test", """hi `!p snip.rv = "Hallo"` End""")
    keys = "test" + EX
    wanted = "hi Hallo End"

class PythonCode_ReferencePlaceholder(_VimTest):
    snippets = ("test", """${1:hi} `!p snip.rv = t[1]+".blah"` End""")
    keys = "test" + EX + "ho"
    wanted = "ho ho.blah End"

class PythonCode_ReferencePlaceholderBefore(_VimTest):
    snippets = ("test", """`!p snip.rv = len(t[1])*"#"`\n${1:some text}""")
    keys = "test" + EX + "Hallo Welt"
    wanted = "##########\nHallo Welt"

class PythonCode_TransformedBeforeMultiLine(_VimTest):
    snippets = ("test", """${1/.+/egal/m} ${1:`!p
snip.rv = "Hallo"`} End""")
    keys = "test" + EX
    wanted = "egal Hallo End"

class PythonCode_MultilineIndented(_VimTest):
    snippets = ("test", """start `!p a = 1
b = 2
if b > a:
    snip.rv = "b isbigger a"
else:
    snip.rv = "a isbigger b"` end""")
    keys = "    test" + EX
    wanted = "    start b isbigger a end"

class PythonCode_SimpleAppend(_VimTest):
    snippets = ("test", """hi `!p snip.rv = "Hallo1"
snip += "Hallo2"` End""")
    keys = "test" + EX
    wanted = "hi Hallo1\nHallo2 End"

class PythonCode_MultiAppend(_VimTest):
    snippets = ("test", """hi `!p snip.rv = "Hallo1"
snip += "Hallo2"
snip += "Hallo3"` End""")
    keys = "test" + EX
    wanted = "hi Hallo1\nHallo2\nHallo3 End"

class PythonCode_MultiAppend(_VimTest):
    snippets = ("test", """hi `!p snip.rv = "Hallo1"
snip += "Hallo2"
snip += "Hallo3"` End""")
    keys = "test" + EX
    wanted = "hi Hallo1\nHallo2\nHallo3 End"

class PythonCode_MultiAppendSimpleIndent(_VimTest):
    snippets = ("test", """hi
`!p snip.rv="Hallo1"
snip += "Hallo2"
snip += "Hallo3"`
End""")
    keys = """
    test""" + EX
    wanted = """
    hi
    Hallo1
    Hallo2
    Hallo3
    End"""

class PythonCode_SimpleMkline(_VimTest):
    snippets = ("test", r"""hi
`!p snip.rv="Hallo1\n"
snip.rv += snip.mkline("Hallo2") + "\n"
snip.rv += snip.mkline("Hallo3")`
End""")
    keys = """
    test""" + EX
    wanted = """
    hi
    Hallo1
    Hallo2
    Hallo3
    End"""

class PythonCode_MultiAppendShift(_VimTest):
    snippets = ("test", r"""hi
`!p snip.rv="i1"
snip += "i1"
snip >> 1
snip += "i2"
snip << 2
snip += "i0"
snip >> 3
snip += "i3"`
End""")
    keys = """
	test""" + EX
    wanted = """
	hi
	i1
	i1
		i2
i0
			i3
	End"""

class PythonCode_MultiAppendShiftMethods(_VimTest):
    snippets = ("test", r"""hi
`!p snip.rv="i1\n"
snip.rv += snip.mkline("i1\n")
snip.shift(1)
snip.rv += snip.mkline("i2\n")
snip.unshift(2)
snip.rv += snip.mkline("i0\n")
snip.shift(3)
snip.rv += snip.mkline("i3")`
End""")
    keys = """
	test""" + EX
    wanted = """
	hi
	i1
	i1
		i2
i0
			i3
	End"""


class PythonCode_ResetIndent(_VimTest):
    snippets = ("test", r"""hi
`!p snip.rv="i1"
snip >> 1
snip += "i2"
snip.reset_indent()
snip += "i1"
snip << 1
snip += "i0"
snip.reset_indent()
snip += "i1"`
End""")
    keys = """
	test""" + EX
    wanted = """
	hi
	i1
		i2
	i1
i0
	i1
	End"""

# TODO
# Different mixes of ts, et, sts, sw
class PythonCode_IndentEtSw(_VimTest):
    def _options_on(self):
        self.send(":set sw=3\n")
        self.send(":set expandtab\n")
    def _options_off(self):
        self.send(":set sw=8\n")
        self.send(":set noexpandtab\n")
    snippets = ("test", r"""hi
`!p snip.rv = "i1"
snip >> 1
snip += "i2"
snip << 2
snip += "i0"
snip >> 1
snip += "i1"
`
End""")
    keys = """   test""" + EX
    wanted = """   hi
   i1
      i2
i0
   i1
   End"""

class PythonCode_IndentEtSwOffset(_VimTest):
    def _options_on(self):
        self.send(":set sw=3\n")
        self.send(":set expandtab\n")
    def _options_off(self):
        self.send(":set sw=8\n")
        self.send(":set noexpandtab\n")
    snippets = ("test", r"""hi
`!p snip.rv = "i1"
snip >> 1
snip += "i2"
snip << 2
snip += "i0"
snip >> 1
snip += "i1"
`
End""")
    keys = """    test""" + EX
    wanted = """    hi
    i1
       i2
 i0
    i1
    End"""

class PythonCode_IndentNoetSwTs(_VimTest):
    def _options_on(self):
        self.send(":set sw=3\n")
        self.send(":set ts=4\n")
    def _options_off(self):
        self.send(":set sw=8\n")
        self.send(":set ts=8\n")
    snippets = ("test", r"""hi
`!p snip.rv = "i1"
snip >> 1
snip += "i2"
snip << 2
snip += "i0"
snip >> 1
snip += "i1"
`
End""")
    keys = """   test""" + EX
    wanted = """   hi
   i1
\t  i2
i0
   i1
   End"""

# Test using 'opt'
class PythonCode_OptExists(_VimTest):
    def _options_on(self):
        self.send(':let g:UStest="yes"\n')
    def _options_off(self):
        self.send(":unlet g:UStest\n")
    snippets = ("test", r"""hi `!p snip.rv = snip.opt("g:UStest") or "no"` End""")
    keys = """test""" + EX
    wanted = """hi yes End"""

class PythonCode_OptNoExists(_VimTest):
    snippets = ("test", r"""hi `!p snip.rv = snip.opt("g:UStest") or "no"` End""")
    keys = """test""" + EX
    wanted = """hi no End"""

# locals
class PythonCode_Locals(_VimTest):
    snippets = ("test", r"""hi `!p snip.locals["a"] = "test"
snip.rv = "nothing"` `!p snip.rv = snip.locals["a"]
` End""")
    keys = """test""" + EX
    wanted = """hi nothing test End"""





###########################
# VimScript Interpolation #
###########################
class TabStop_VimScriptInterpolation_SimpleExample(_VimTest):
    snippets = ("test", """hi `!v indent(".")` End""")
    keys = "    test" + EX
    wanted = "    hi 4 End"

# TODO: pasting with <C-R> while mirroring, also multiline
# TODO: Multiline text pasting
# TODO: option to avoid snippet expansion when not only indent in front

#############
# EXPANDTAB #
#############
class _ExpandTabs(_VimTest):
    def _options_on(self):
        self.send(":set ts=3\n")
        self.send(":set expandtab\n")
    def _options_off(self):
        self.send(":set ts=8\n")
        self.send(":set noexpandtab\n")

class RecTabStopsWithExpandtab_SimpleExample_ECR(_ExpandTabs):
    snippets = ("m", "\tBlaahblah \t\t  ")
    keys = "m" + EX
    wanted = "   Blaahblah         "

class RecTabStopsWithExpandtab_SpecialIndentProblem_ECR(_ExpandTabs):
    snippets = (
        ("m1", "Something"),
        ("m", "\t$0"),
    )
    keys = "m" + EX + "m1" + EX + '\nHallo'
    wanted = "   Something\n        Hallo"
    def _options_on(self):
        _ExpandTabs._options_on(self)
        self.send(":set indentkeys=o,O,*<Return>,<>>,{,}\n")
        self.send(":set indentexpr=8\n")
    def _options_off(self):
        _ExpandTabs._options_off(self)
        self.send(":set indentkeys=\n")
        self.send(":set indentexpr=\n")



###############################
# Recursive (Nested) Snippets #
###############################
class RecTabStops_SimpleCase_ExceptCorrectResult(_VimTest):
    snippets = ("m", "[ ${1:first}  ${2:sec} ]")
    keys = "m" + EX + "m" + EX + "hello" + JF + "world" + JF + "end"
    wanted = "[ [ hello  world ]  end ]"
class RecTabStops_SimpleCaseLeaveSecondSecond_ExceptCorrectResult(_VimTest):
    snippets = ("m", "[ ${1:first}  ${2:sec} ]")
    keys = "m" + EX + "m" + EX + "hello" + JF + "world" + JF + JF + "end"
    wanted = "[ [ hello  world ]  sec ]end"
class RecTabStops_SimpleCaseLeaveFirstSecond_ExceptCorrectResult(_VimTest):
    snippets = ("m", "[ ${1:first}  ${2:sec} ]")
    keys = "m" + EX + "m" + EX + "hello" + JF + JF + "world" + JF + "end"
    wanted = "[ [ hello  sec ]  world ]end"

class RecTabStops_InnerWOTabStop_ECR(_VimTest):
    snippets = (
        ("m1", "Just some Text"),
        ("m", "[ ${1:first}  ${2:sec} ]"),
    )
    keys = "m" + EX + "m1" + EX + "hi" + JF + "two" + JF + "end"
    wanted = "[ Just some Texthi  two ]end"
class RecTabStops_InnerWOTabStopTwiceDirectly_ECR(_VimTest):
    snippets = (
        ("m1", "JST"),
        ("m", "[ ${1:first}  ${2:sec} ]"),
    )
    keys = "m" + EX + "m1" + EX + " m1" + EX + "hi" + JF + "two" + JF + "end"
    wanted = "[ JST JSThi  two ]end"
class RecTabStops_InnerWOTabStopTwice_ECR(_VimTest):
    snippets = (
        ("m1", "JST"),
        ("m", "[ ${1:first}  ${2:sec} ]"),
    )
    keys = "m" + EX + "m1" + EX + JF + "m1" + EX + "hi" + JF + "end"
    wanted = "[ JST  JSThi ]end"
class RecTabStops_OuterOnlyWithZeroTS_ECR(_VimTest):
    snippets = (
        ("m", "A $0 B"),
        ("m1", "C $1 D $0 E"),
    )
    keys = "m" + EX + "m1" + EX + "CD" + JF + "DE"
    wanted = "A C CD D DE E B"
class RecTabStops_OuterOnlyWithZero_ECR(_VimTest):
    snippets = (
        ("m", "A $0 B"),
        ("m1", "C $1 D $0 E"),
    )
    keys = "m" + EX + "m1" + EX + "CD" + JF + "DE"
    wanted = "A C CD D DE E B"
class RecTabStops_ExpandedInZeroTS_ECR(_VimTest):
    snippets = (
        ("m", "A $0 B $1"),
        ("m1", "C $1 D $0 E"),
    )
    keys = "m" + EX + "hi" + JF + "m1" + EX + "CD" + JF + "DE"
    wanted = "A C CD D DE E B hi"
class RecTabStops_ExpandedInZeroTSTwice_ECR(_VimTest):
    snippets = (
        ("m", "A $0 B $1"),
        ("m1", "C $1 D $0 E"),
    )
    keys = "m" + EX + "hi" + JF + "m" + EX + "again" + JF + "m1" + \
            EX + "CD" + JF + "DE"
    wanted = "A A C CD D DE E B again B hi"
class RecTabStops_ExpandedInZeroTSSecondTimeIgnoreZTS_ECR(_VimTest):
    snippets = (
        ("m", "A $0 B $1"),
        ("m1", "C $1 D $0 E"),
    )
    keys = "m" + EX + "hi" + JF + "m" + EX + "m1" + EX + "CD" + JF + "DE"
    wanted = "A A DE B C CD D  E B hi"

class RecTabStops_MirrorInnerSnippet_ECR(_VimTest):
    snippets = (
        ("m", "[ $1 $2 ] $1"),
        ("m1", "ASnip $1 ASnip $2 ASnip"),
    )
    keys = "m" + EX + "m1" + EX + "Hallo" + JF + "Hi" + JF + "two" + JF + "end"
    wanted = "[ ASnip Hallo ASnip Hi ASnip two ] ASnip Hallo ASnip Hi ASnipend"

class RecTabStops_NotAtBeginningOfTS_ExceptCorrectResult(_VimTest):
    snippets = ("m", "[ ${1:first}  ${2:sec} ]")
    keys = "m" + EX + "hello m" + EX + "hi" + JF + "two" + JF + "three" + \
            JF + "end"
    wanted = "[ hello [ hi  two ]  three ]end"
class RecTabStops_InNewlineInTabstop_ExceptCorrectResult(_VimTest):
    sleeptime = 0.09 # Do this very slowly
    snippets = ("m", "[ ${1:first}  ${2:sec} ]")
    keys = "m" + EX + "hello\nm" + EX + "hi" + JF + "two" + JF + "three" + \
            JF + "end"
    wanted = "[ hello\n[ hi  two ]  three ]end"
class RecTabStops_InNewlineInTabstopNotAtBeginOfLine_ECR(_VimTest):
    snippets = ("m", "[ ${1:first}  ${2:sec} ]")
    keys = "m" + EX + "hello\nhello again m" + EX + "hi" + JF + "two" + \
            JF + "three" + JF + "end"
    wanted = "[ hello\nhello again [ hi  two ]  three ]end"

class RecTabStops_InNewlineMultiline_ECR(_VimTest):
    snippets = ("m", "M START\n$0\nM END")
    keys = "m" + EX + "m" + EX
    wanted = "M START\nM START\n\nM END\nM END"
class RecTabStops_InNewlineManualIndent_ECR(_VimTest):
    snippets = ("m", "M START\n$0\nM END")
    keys = "m" + EX + "    m" + EX + "hi"
    wanted = "M START\n    M START\n    hi\n    M END\nM END"
class RecTabStops_InNewlineManualIndentTextInFront_ECR(_VimTest):
    snippets = ("m", "M START\n$0\nM END")
    keys = "m" + EX + "    hallo m" + EX + "hi"
    wanted = "M START\n    hallo M START\n    hi\n    M END\nM END"
class RecTabStops_InNewlineMultilineWithIndent_ECR(_VimTest):
    snippets = ("m", "M START\n    $0\nM END")
    keys = "m" + EX + "m" + EX + "hi"
    wanted = "M START\n    M START\n        hi\n    M END\nM END"
class RecTabStops_InNewlineMultilineWithNonZeroTS_ECR(_VimTest):
    snippets = ("m", "M START\n    $1\nM END -> $0")
    keys = "m" + EX + "m" + EX + "hi" + JF + "hallo"
    wanted = "M START\n    M START\n        hi\n    M END -> \n" \
        "M END -> hallo"

class RecTabStops_BarelyNotLeavingInner_ECR(_VimTest):
    snippets = (
        ("m", "[ ${1:first} ${2:sec} ]"),
    )
    keys = "m" + EX + "m" + EX + "a" + 3*ARR_L + JF + "hallo" + \
            JF + "world" + JF + "end"
    wanted = "[ [ a hallo ] world ]end"
class RecTabStops_LeavingInner_ECR(_VimTest):
    snippets = (
        ("m", "[ ${1:first} ${2:sec} ]"),
    )
    keys = "m" + EX + "m" + EX + "a" + 4*ARR_L + JF + "hallo" + \
            JF + "world"
    wanted = "[ [ a sec ] hallo ]world"
class RecTabStops_LeavingInnerInner_ECR(_VimTest):
    snippets = (
        ("m", "[ ${1:first} ${2:sec} ]"),
    )
    keys = "m" + EX + "m" + EX + "m" + EX + "a" + 4*ARR_L + JF + "hallo" + \
            JF + "world" + JF + "end"
    wanted = "[ [ [ a sec ] hallo ] world ]end"
class RecTabStops_LeavingInnerInnerTwo_ECR(_VimTest):
    snippets = (
        ("m", "[ ${1:first} ${2:sec} ]"),
    )
    keys = "m" + EX + "m" + EX + "m" + EX + "a" + 6*ARR_L + JF + "hallo" + \
            JF + "end"
    wanted = "[ [ [ a sec ] sec ] hallo ]end"


class RecTabStops_IgnoreZeroTS_ECR(_VimTest):
    snippets = (
        ("m1", "[ ${1:first} $0 ${2:sec} ]"),
        ("m", "[ ${1:first} ${2:sec} ]"),
    )
    keys = "m" + EX + "m1" + EX + "hi" + JF + "two" + \
            JF + "three" + JF + "end"
    wanted = "[ [ hi  two ] three ]end"
class RecTabStops_MirroredZeroTS_ECR(_VimTest):
    snippets = (
        ("m1", "[ ${1:first} ${0:Year, some default text} $0 ${2:sec} ]"),
        ("m", "[ ${1:first} ${2:sec} ]"),
    )
    keys = "m" + EX + "m1" + EX + "hi" + JF + "two" + \
            JF + "three" + JF + "end"
    wanted = "[ [ hi   two ] three ]end"

###########
# MIRRORS #
###########
class TextTabStopTextAfterTab_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1 Hinten\n$1")
    keys = "test" + EX + "hallo"
    wanted = "hallo Hinten\nhallo"
class TextTabStopTextBeforeTab_ExceptCorrectResult(_VimTest):
    snippets = ("test", "Vorne $1\n$1")
    keys = "test" + EX + "hallo"
    wanted = "Vorne hallo\nhallo"
class TextTabStopTextSurroundedTab_ExceptCorrectResult(_VimTest):
    snippets = ("test", "Vorne $1 Hinten\n$1")
    keys = "test" + EX + "hallo test"
    wanted = "Vorne hallo test Hinten\nhallo test"

class TextTabStopTextBeforeMirror_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1\nVorne $1")
    keys = "test" + EX + "hallo"
    wanted = "hallo\nVorne hallo"
class TextTabStopAfterMirror_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1\n$1 Hinten")
    keys = "test" + EX + "hallo"
    wanted = "hallo\nhallo Hinten"
class TextTabStopSurroundMirror_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1\nVorne $1 Hinten")
    keys = "test" + EX + "hallo welt"
    wanted = "hallo welt\nVorne hallo welt Hinten"
class TextTabStopAllSurrounded_ExceptCorrectResult(_VimTest):
    snippets = ("test", "ObenVorne $1 ObenHinten\nVorne $1 Hinten")
    keys = "test" + EX + "hallo welt"
    wanted = "ObenVorne hallo welt ObenHinten\nVorne hallo welt Hinten"

class MirrorBeforeTabstopLeave_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1:this is it} $1")
    keys = "test" + EX
    wanted = "this is it this is it this is it"
class MirrorBeforeTabstopOverwrite_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1:this is it} $1")
    keys = "test" + EX + "a"
    wanted = "a a a"

class TextTabStopSimpleMirrorMultiline_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1\n$1")
    keys = "test" + EX + "hallo"
    wanted = "hallo\nhallo"
class SimpleMirrorMultilineMany_ExceptCorrectResult(_VimTest):
    snippets = ("test", "    $1\n$1\na$1b\n$1\ntest $1 mich")
    keys = "test" + EX + "hallo"
    wanted = "    hallo\nhallo\nahallob\nhallo\ntest hallo mich"
class MultilineTabStopSimpleMirrorMultiline_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1\n\n$1\n\n$1")
    keys = "test" + EX + "hallo Du\nHi"
    wanted = "hallo Du\nHi\n\nhallo Du\nHi\n\nhallo Du\nHi"
class MultilineTabStopSimpleMirrorMultiline1_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1\n$1\n$1")
    keys = "test" + EX + "hallo Du\nHi"
    wanted = "hallo Du\nHi\nhallo Du\nHi\nhallo Du\nHi"
class MultilineTabStopSimpleMirrorDeleteInLine_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1\n$1\n$1")
    keys = "test" + EX + "hallo Du\nHi\b\bAch Blah"
    wanted = "hallo Du\nAch Blah\nhallo Du\nAch Blah\nhallo Du\nAch Blah"
class TextTabStopSimpleMirrorMultilineMirrorInFront_ECR(_VimTest):
    snippets = ("test", "$1\n${1:sometext}")
    keys = "test" + EX + "hallo\nagain"
    wanted = "hallo\nagain\nhallo\nagain"

class SimpleMirrorDelete_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1\n$1")
    keys = "test" + EX + "hallo\b\b"
    wanted = "hal\nhal"

class SimpleMirrorSameLine_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1 $1")
    keys = "test" + EX + "hallo"
    wanted = "hallo hallo"
class Transformation_SimpleMirrorSameLineBeforeTabDefVal_ECR(_VimTest):
    snippets = ("test", "$1 ${1:replace me}")
    keys = "test" + EX + "hallo foo"
    wanted = "hallo foo hallo foo"
class SimpleMirrorSameLineMany_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1 $1 $1 $1")
    keys = "test" + EX + "hallo du"
    wanted = "hallo du hallo du hallo du hallo du"
class SimpleMirrorSameLineManyMultiline_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1 $1 $1 $1")
    keys = "test" + EX + "hallo du\nwie gehts"
    wanted = "hallo du\nwie gehts hallo du\nwie gehts hallo du\nwie gehts" \
            " hallo du\nwie gehts"
class SimpleMirrorDeleteSomeEnterSome_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1\n$1")
    keys = "test" + EX + "hallo\b\bhups"
    wanted = "halhups\nhalhups"


class SimpleTabstopWithDefaultSimpelType_ExceptCorrectResult(_VimTest):
    snippets = ("test", "ha ${1:defa}\n$1")
    keys = "test" + EX + "world"
    wanted = "ha world\nworld"
class SimpleTabstopWithDefaultComplexType_ExceptCorrectResult(_VimTest):
    snippets = ("test", "ha ${1:default value} $1\nanother: $1 mirror")
    keys = "test" + EX + "world"
    wanted = "ha world world\nanother: world mirror"
class SimpleTabstopWithDefaultSimpelKeep_ExceptCorrectResult(_VimTest):
    snippets = ("test", "ha ${1:defa}\n$1")
    keys = "test" + EX
    wanted = "ha defa\ndefa"
class SimpleTabstopWithDefaultComplexKeep_ExceptCorrectResult(_VimTest):
    snippets = ("test", "ha ${1:default value} $1\nanother: $1 mirror")
    keys = "test" + EX
    wanted = "ha default value default value\nanother: default value mirror"

class TabstopWithMirrorManyFromAll_ExceptCorrectResult(_VimTest):
    snippets = ("test", "ha $5 ${1:blub} $4 $0 ${2:$1.h} $1 $3 ${4:More}")
    keys = "test" + EX + "hi" + JF + "hu" + JF + "hub" + JF + "hulla" + \
            JF + "blah" + JF + "end"
    wanted = "ha blah hi hulla end hu hi hub hulla"
class TabstopWithMirrorInDefaultNoType_ExceptCorrectResult(_VimTest):
    snippets = ("test", "ha ${1:blub} ${2:$1.h}")
    keys = "test" + EX
    wanted = "ha blub blub.h"
class TabstopWithMirrorInDefaultTwiceAndExtra_ExceptCorrectResult(_VimTest):
    snippets = ("test", "ha $1 ${2:$1.h $1.c}\ntest $1")
    keys = "test" + EX + "stdin"
    wanted = "ha stdin stdin.h stdin.c\ntest stdin"
class TabstopWithMirrorInDefaultMultipleLeave_ExceptCorrectResult(_VimTest):
    snippets = ("test", "ha $1 ${2:snip} ${3:$1.h $2}")
    keys = "test" + EX + "stdin"
    wanted = "ha stdin snip stdin.h snip"
class TabstopWithMirrorInDefaultMultipleOverwrite_ExceptCorrectResult(_VimTest):
    snippets = ("test", "ha $1 ${2:snip} ${3:$1.h $2}")
    keys = "test" + EX + "stdin" + JF + "do snap"
    wanted = "ha stdin do snap stdin.h do snap"
class TabstopWithMirrorInDefaultOverwrite_ExceptCorrectResult(_VimTest):
    snippets = ("test", "ha $1 ${2:$1.h}")
    keys = "test" + EX + "stdin" + JF + "overwritten"
    wanted = "ha stdin overwritten"

class MirrorRealLifeExample_ExceptCorrectResult(_VimTest):
    snippets = (
        ("for", "for(size_t ${2:i} = 0; $2 < ${1:count}; ${3:++$2})" \
         "\n{\n" + EX + "${0:/* code */}\n}"),
    )
    keys ="for" + EX + "100" + JF + "avar\b\b\b\ba_variable" + JF + \
            "a_variable *= 2" + JF + "// do nothing"
    wanted = """for(size_t a_variable = 0; a_variable < 100; a_variable *= 2)
{
\t// do nothing
}"""


###################
# TRANSFORMATIONS #
###################
class Transformation_SimpleCase_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1/foo/batzl/}")
    keys = "test" + EX + "hallo foo boy"
    wanted = "hallo foo boy hallo batzl boy"
class Transformation_SimpleCaseNoTransform_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1/foo/batzl/}")
    keys = "test" + EX + "hallo"
    wanted = "hallo hallo"
class Transformation_SimpleCaseTransformInFront_ExceptCorrectResult(_VimTest):
    snippets = ("test", "${1/foo/batzl/} $1")
    keys = "test" + EX + "hallo foo"
    wanted = "hallo batzl hallo foo"
class Transformation_SimpleCaseTransformInFrontDefVal_ECR(_VimTest):
    snippets = ("test", "${1/foo/batzl/} ${1:replace me}")
    keys = "test" + EX + "hallo foo"
    wanted = "hallo batzl hallo foo"
class Transformation_MultipleTransformations_ECR(_VimTest):
    snippets = ("test", "${1:Some Text}${1/.+/\U$0\E/}\n${1/.+/\L$0\E/}")
    keys = "test" + EX + "SomE tExt "
    wanted = "SomE tExt SOME TEXT \nsome text "
class Transformation_TabIsAtEndAndDeleted_ECR(_VimTest):
    snippets = ("test", "${1/.+/is something/}${1:some}")
    keys = "hallo test" + EX + "some\b\b\b\b\b"
    wanted = "hallo "
class Transformation_TabIsAtEndAndDeleted1_ECR(_VimTest):
    snippets = ("test", "${1/.+/is something/}${1:some}")
    keys = "hallo test" + EX + "some\b\b\b\bmore"
    wanted = "hallo is somethingmore"
class Transformation_TabIsAtEndNoTextLeave_ECR(_VimTest):
    snippets = ("test", "${1/.+/is something/}${1}")
    keys = "hallo test" + EX
    wanted = "hallo "
class Transformation_TabIsAtEndNoTextType_ECR(_VimTest):
    snippets = ("test", "${1/.+/is something/}${1}")
    keys = "hallo test" + EX + "b"
    wanted = "hallo is somethingb"
class Transformation_InsideTabLeaveAtDefault_ECR(_VimTest):
    snippets = ("test", r"$1 ${2:${1/.+/(?0:defined $0)/}}")
    keys = "test" + EX + "sometext" + JF
    wanted = "sometext defined sometext"
class Transformation_InsideTabOvertype_ECR(_VimTest):
    snippets = ("test", r"$1 ${2:${1/.+/(?0:defined $0)/}}")
    keys = "test" + EX + "sometext" + JF + "overwrite"
    wanted = "sometext overwrite"


class Transformation_Backreference_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1/([ab])oo/$1ull/}")
    keys = "test" + EX + "foo boo aoo"
    wanted = "foo boo aoo foo bull aoo"
class Transformation_BackreferenceTwice_ExceptCorrectResult(_VimTest):
    snippets = ("test", r"$1 ${1/(dead) (par[^ ]*)/this $2 is a bit $1/}")
    keys = "test" + EX + "dead parrot"
    wanted = "dead parrot this parrot is a bit dead"

class Transformation_CleverTransformUpercaseChar_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1/(.)/\u$1/}")
    keys = "test" + EX + "hallo"
    wanted = "hallo Hallo"
class Transformation_CleverTransformLowercaseChar_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1/(.*)/\l$1/}")
    keys = "test" + EX + "Hallo"
    wanted = "Hallo hallo"
class Transformation_CleverTransformLongUpper_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1/(.*)/\U$1\E/}")
    keys = "test" + EX + "hallo"
    wanted = "hallo HALLO"
class Transformation_CleverTransformLongLower_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1/(.*)/\L$1\E/}")
    keys = "test" + EX + "HALLO"
    wanted = "HALLO hallo"

class Transformation_ConditionalInsertionSimple_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1/(^a).*/(?0:began with an a)/}")
    keys = "test" + EX + "a some more text"
    wanted = "a some more text began with an a"
class Transformation_CIBothDefinedNegative_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1/(?:(^a)|(^b)).*/(?1:yes:no)/}")
    keys = "test" + EX + "b some"
    wanted = "b some no"
class Transformation_CIBothDefinedPositive_ExceptCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1/(?:(^a)|(^b)).*/(?1:yes:no)/}")
    keys = "test" + EX + "a some"
    wanted = "a some yes"
class Transformation_ConditionalInsertRWEllipsis_ECR(_VimTest):
    snippets = ("test", r"$1 ${1/(\w+(?:\W+\w+){,7})\W*(.+)?/$1(?2:...)/}")
    keys = "test" + EX + "a b  c d e f ghhh h oha"
    wanted = "a b  c d e f ghhh h oha a b  c d e f ghhh h..."
class Transformation_ConditionalInConditional_ECR(_VimTest):
    snippets = ("test", r"$1 ${1/^.*?(-)?(>)?$/(?2::(?1:>:.))/}")
    keys = "test" + EX + "hallo" + ESC + "$a\n" + \
           "test" + EX + "hallo-" + ESC + "$a\n" + \
           "test" + EX + "hallo->"
    wanted = "hallo .\nhallo- >\nhallo-> "

class Transformation_CINewlines_ECR(_VimTest):
    snippets = ("test", r"$1 ${1/, */\n/}")
    keys = "test" + EX + "test, hallo"
    wanted = "test, hallo test\nhallo"
class Transformation_CIEscapedParensinReplace_ECR(_VimTest):
    snippets = ("test", r"$1 ${1/hal((?:lo)|(?:ul))/(?1:ha\($1\))/}")
    keys = "test" + EX + "test, halul"
    wanted = "test, halul test, ha(ul)"

class Transformation_OptionIgnoreCase_ECR(_VimTest):
    snippets = ("test", r"$1 ${1/test/blah/i}")
    keys = "test" + EX + "TEST"
    wanted = "TEST blah"
class Transformation_OptionReplaceGlobal_ECR(_VimTest):
    snippets = ("test", r"$1 ${1/, */-/g}")
    keys = "test" + EX + "a, nice, building"
    wanted = "a, nice, building a-nice-building"
class Transformation_OptionReplaceGlobalMatchInReplace_ECR(_VimTest):
    snippets = ("test", r"$1 ${1/, */, /g}")
    keys = "test" + EX + "a, nice,   building"
    wanted = "a, nice,   building a, nice, building"

###################
# CURSOR MOVEMENT #
###################
class CursorMovement_Multiline_ECR(_VimTest):
    snippets = ("test", r"$1 ${1:a tab}")
    keys = "test" + EX + "this is something\nvery nice\nnot" + JF + "more text"
    wanted = "this is something\nvery nice\nnot " \
            "this is something\nvery nice\nnotmore text"


######################
# INSERT MODE MOVING #
######################
class IMMoving_CursorsKeys_ECR(_VimTest):
    snippets = ("test", "${1:Some}")
    keys = "test" + EX + "text" + 3*ARR_U + 6*ARR_D
    wanted = "text"
class IMMoving_DoNotAcceptInputWhenMoved_ECR(_VimTest):
    snippets = ("test", r"$1 ${1:a tab}")
    keys = "test" + EX + "this" + ARR_L + "hallo"
    wanted = "this thihallos"
class IMMoving_NoExiting_ECR(_VimTest):
    snippets = ("test", r"$1 ${2:a tab} ${1:Tab}")
    keys = "hello test this" + ESC + "02f i" + EX + "tab" + 7*ARR_L + \
            JF + "hallo"
    wanted = "hello tab hallo tab this"
class IMMoving_NoExitingEventAtEnd_ECR(_VimTest):
    snippets = ("test", r"$1 ${2:a tab} ${1:Tab}")
    keys = "hello test this" + ESC + "02f i" + EX + "tab" + JF + "hallo"
    wanted = "hello tab hallo tab this"
class IMMoving_ExitWhenOutsideRight_ECR(_VimTest):
    snippets = ("test", r"$1 ${2:blub} ${1:Tab}")
    keys = "hello test this" + ESC + "02f i" + EX + "tab" + ARR_R + JF + "hallo"
    wanted = "hello tab blub tab hallothis"
class IMMoving_NotExitingWhenBarelyOutsideLeft_ECR(_VimTest):
    snippets = ("test", r"${1:Hi} ${2:blub}")
    keys = "hello test this" + ESC + "02f i" + EX + "tab" + 3*ARR_L + \
            JF + "hallo"
    wanted = "hello tab hallo this"
class IMMoving_ExitWhenOutsideLeft_ECR(_VimTest):
    snippets = ("test", r"${1:Hi} ${2:blub}")
    keys = "hello test this" + ESC + "02f i" + EX + "tab" + 4*ARR_L + \
            JF + "hallo"
    wanted = "hellohallo tab blub this"
class IMMoving_ExitWhenOutsideAbove_ECR(_VimTest):
    snippets = ("test", "${1:Hi}\n${2:blub}")
    keys = "hello test this" + ESC + "02f i" + EX + "tab" + 1*ARR_U + JF + \
            "\nhallo"
    wanted = "hallo\nhello tab\nblub this"
class IMMoving_ExitWhenOutsideBelow_ECR(_VimTest):
    snippets = ("test", "${1:Hi}\n${2:blub}")
    keys = "hello test this" + ESC + "02f i" + EX + "tab" + 2*ARR_D + JF + \
            "testhallo\n"
    wanted = "hello tab\nblub this\ntesthallo"


####################
# PROPER INDENTING #
####################
class ProperIndenting_SimpleCase_ECR(_VimTest):
    snippets = ("test", "for\n    blah")
    keys = "    test" + EX + "Hui"
    wanted = "    for\n        blahHui"
class ProperIndenting_SingleLineNoReindenting_ECR(_VimTest):
    snippets = ("test", "hui")
    keys = "    test" + EX + "blah"
    wanted = "    huiblah"
class ProperIndenting_AutoIndentAndNewline_ECR(_VimTest):
    snippets = ("test", "hui")
    keys = "    test" + EX + "\n"+ "blah"
    wanted = "    hui\n    blah"
    def _options_on(self):
        self.send(":set autoindent\n")
    def _options_off(self):
        self.send(":set noautoindent\n")

####################
# COMPLETION TESTS #
####################
class Completion_SimpleExample_ECR(_VimTest):
    snippets = ("test", "$1 ${1:blah}")
    keys = "superkallifragilistik\ntest" + EX + "sup" + COMPL_KW + \
            COMPL_ACCEPT + " some more"
    wanted = "superkallifragilistik\nsuperkallifragilistik some more " \
            "superkallifragilistik some more"

# We need >2 different words with identical starts to create the
# popup-menu:
COMPLETION_OPTIONS = "completion1\ncompletion2\n"

class Completion_ForwardsJumpWithoutCOMPL_ACCEPT(_VimTest):
    # completions should not be truncated when JF is activated without having
    # pressed COMPL_ACCEPT (Bug #598903)
    snippets = ("test", "$1 $2")
    keys = COMPLETION_OPTIONS + "test" + EX + "com" + COMPL_KW + JF + "foo"
    wanted = COMPLETION_OPTIONS + "completion1 foo"

class Completion_BackwardsJumpWithoutCOMPL_ACCEPT(_VimTest):
    # completions should not be truncated when JB is activated without having
    # pressed COMPL_ACCEPT (Bug #598903)
    snippets = ("test", "$1 $2")
    keys = COMPLETION_OPTIONS + "test" + EX + "foo" + JF + "com" + COMPL_KW + \
           JB + "foo"
    wanted = COMPLETION_OPTIONS + "foo completion1"

###################
# SNIPPET OPTIONS #
###################
class SnippetOptions_OverwriteExisting_ECR(_VimTest):
    snippets = (
     ("test", "${1:Hallo}", "Types Hallo"),
     ("test", "${1:World}", "Types World"),
     ("test", "We overwrite", "Overwrite the two", "!"),
    )
    keys = "test" + EX
    wanted = "We overwrite"
class SnippetOptions_OverwriteTwice_ECR(_VimTest):
    snippets = (
        ("test", "${1:Hallo}", "Types Hallo"),
        ("test", "${1:World}", "Types World"),
        ("test", "We overwrite", "Overwrite the two", "!"),
        ("test", "again", "Overwrite again", "!"),
    )
    keys = "test" + EX
    wanted = "again"
class SnippetOptions_OverwriteThenChoose_ECR(_VimTest):
    snippets = (
        ("test", "${1:Hallo}", "Types Hallo"),
        ("test", "${1:World}", "Types World"),
        ("test", "We overwrite", "Overwrite the two", "!"),
        ("test", "No overwrite", "Not overwritten", ""),
    )
    keys = "test" + EX + "1\n\n" + "test" + EX + "2\n"
    wanted = "We overwrite\nNo overwrite"
class SnippetOptions_OnlyExpandWhenWSInFront_Expand(_VimTest):
    snippets = ("test", "Expand me!", "", "b")
    keys = "test" + EX
    wanted = "Expand me!"
class SnippetOptions_OnlyExpandWhenWSInFront_Expand2(_VimTest):
    snippets = ("test", "Expand me!", "", "b")
    keys = "   test" + EX
    wanted = "   Expand me!"
class SnippetOptions_OnlyExpandWhenWSInFront_DontExpand(_VimTest):
    snippets = ("test", "Expand me!", "", "b")
    keys = "a test" + EX
    wanted = "a test" + EX
class SnippetOptions_OnlyExpandWhenWSInFront_OneWithOneWO(_VimTest):
    snippets = (
        ("test", "Expand me!", "", "b"),
        ("test", "not at beginning", "", ""),
    )
    keys = "a test" + EX
    wanted = "a not at beginning"
class SnippetOptions_OnlyExpandWhenWSInFront_OneWithOneWOChoose(_VimTest):
    snippets = (
        ("test", "Expand me!", "", "b"),
        ("test", "not at beginning", "", ""),
    )
    keys = "  test" + EX + "1\n"
    wanted = "  Expand me!"


class SnippetOptions_ExpandInwordSnippets_SimpleExpand(_VimTest):
    snippets = (("test", "Expand me!", "", "i"), )
    keys = "atest" + EX
    wanted = "aExpand me!"
class SnippetOptions_ExpandInwordSnippets_ExpandSingle(_VimTest):
    snippets = (("test", "Expand me!", "", "i"), )
    keys = "test" + EX
    wanted = "Expand me!"
class SnippetOptions_ExpandInwordSnippetsWithOtherChars_Expand(_VimTest):
    snippets = (("test", "Expand me!", "", "i"), )
    keys = "$test" + EX
    wanted = "$Expand me!"
class SnippetOptions_ExpandInwordSnippetsWithOtherChars_Expand2(_VimTest):
    snippets = (("test", "Expand me!", "", "i"), )
    keys = "-test" + EX
    wanted = "-Expand me!"
class SnippetOptions_ExpandInwordSnippetsWithOtherChars_Expand3(_VimTest):
    snippets = (("test", "Expand me!", "", "i"), )
    keys = "ätest" + EX
    wanted = "äExpand me!"

class _SnippetOptions_ExpandWordSnippets(_VimTest):
    snippets = (("test", "Expand me!", "", "w"), )
class SnippetOptions_ExpandWordSnippets_NormalExpand(
        _SnippetOptions_ExpandWordSnippets):
    keys = "test" + EX
    wanted = "Expand me!"
class SnippetOptions_ExpandWordSnippets_NoExpand(
    _SnippetOptions_ExpandWordSnippets):
    keys = "atest" + EX
    wanted = "atest" + EX
class SnippetOptions_ExpandWordSnippets_ExpandSuffix(
    _SnippetOptions_ExpandWordSnippets):
    keys = "a-test" + EX
    wanted = "a-Expand me!"
class SnippetOptions_ExpandWordSnippets_ExpandSuffix2(
    _SnippetOptions_ExpandWordSnippets):
    keys = "a(test" + EX
    wanted = "a(Expand me!"
class SnippetOptions_ExpandWordSnippets_ExpandSuffix3(
    _SnippetOptions_ExpandWordSnippets):
    keys = "[[test" + EX
    wanted = "[[Expand me!"

#################
# REGEX MATCHES #
#################
class SnippetOptions_Regex_Expand(_VimTest):
    snippets = ("(test)", "Expand me!", "", "r")
    keys = "test" + EX
    wanted = "Expand me!"
class SnippetOptions_Regex_Multiple(_VimTest):
    snippets = ("(test *)+", "Expand me!", "", "r")
    keys = "test test test" + EX
    wanted = "Expand me!"

class _Regex_Self(_VimTest):
    snippets = (r"((?<=\W)|^)(\.)", "self.", "", "r")
class SnippetOptions_Regex_Self_Start(_Regex_Self):
    keys = "." + EX
    wanted = "self."
class SnippetOptions_Regex_Self_Space(_Regex_Self):
    keys = " ." + EX
    wanted = " self."
class SnippetOptions_Regex_Self_TextAfter(_Regex_Self):
    keys = " .a" + EX
    wanted = " .a" + EX
class SnippetOptions_Regex_Self_TextBefore(_Regex_Self):
    keys = "a." + EX
    wanted = "a." + EX


######################
# SELECTING MULTIPLE #
######################
class _MultipleMatches(_VimTest):
    snippets = ( ("test", "Case1", "This is Case 1"),
                 ("test", "Case2", "This is Case 2") )
class Multiple_SimpleCaseSelectFirst_ECR(_MultipleMatches):
    keys = "test" + EX + "1\n"
    wanted = "Case1"
class Multiple_SimpleCaseSelectSecond_ECR(_MultipleMatches):
    keys = "test" + EX + "2\n"
    wanted = "Case2"
class Multiple_SimpleCaseSelectTooHigh_ESelectLast(_MultipleMatches):
    keys = "test" + EX + "5\n"
    wanted = "Case2"
class Multiple_SimpleCaseSelectZero_EEscape(_MultipleMatches):
    keys = "test" + EX + "0\n" + "hi"
    wanted = "testhi"
class Multiple_SimpleCaseEscapeOut_ECR(_MultipleMatches):
    keys = "test" + EX + ESC + "hi"
    wanted = "testhi"
class Multiple_ManySnippetsOneTrigger_ECR(_VimTest):
    # Snippet definition {{{
    snippets = (
        ("test", "Case1", "This is Case 1"),
        ("test", "Case2", "This is Case 2"),
        ("test", "Case3", "This is Case 3"),
        ("test", "Case4", "This is Case 4"),
        ("test", "Case5", "This is Case 5"),
        ("test", "Case6", "This is Case 6"),
        ("test", "Case7", "This is Case 7"),
        ("test", "Case8", "This is Case 8"),
        ("test", "Case9", "This is Case 9"),
        ("test", "Case10", "This is Case 10"),
        ("test", "Case11", "This is Case 11"),
        ("test", "Case12", "This is Case 12"),
        ("test", "Case13", "This is Case 13"),
        ("test", "Case14", "This is Case 14"),
        ("test", "Case15", "This is Case 15"),
        ("test", "Case16", "This is Case 16"),
        ("test", "Case17", "This is Case 17"),
        ("test", "Case18", "This is Case 18"),
        ("test", "Case19", "This is Case 19"),
        ("test", "Case20", "This is Case 20"),
        ("test", "Case21", "This is Case 21"),
        ("test", "Case22", "This is Case 22"),
        ("test", "Case23", "This is Case 23"),
        ("test", "Case24", "This is Case 24"),
        ("test", "Case25", "This is Case 25"),
        ("test", "Case26", "This is Case 26"),
        ("test", "Case27", "This is Case 27"),
        ("test", "Case28", "This is Case 28"),
        ("test", "Case29", "This is Case 29"),
    ) # }}}
    sleeptime = 0.09 # Do this very slowly
    keys = "test" + EX + " " + ESC + ESC + "ahi"
    wanted = "testhi"


##################################
# LIST OF ALL AVAILABLE SNIPPETS #
##################################
class _ListAllSnippets(_VimTest):
    snippets = ( ("testblah", "BLAAH", "Say BLAH"),
                 ("test", "TEST ONE", "Say tst one"),
                 ("aloha", "OHEEEE",   "Say OHEE"),
               )

class ListAllAvailable_NothingTyped_ExceptCorrectResult(_ListAllSnippets):
    keys = "" + LS + "3\n"
    wanted = "OHEEEE"
class ListAllAvailable_testtyped_ExceptCorrectResult(_ListAllSnippets):
    keys = "hallo test" + LS + "1\n"
    wanted = "hallo BLAAH"
class ListAllAvailable_testtypedSecondOpt_ExceptCorrectResult(_ListAllSnippets):
    keys = "hallo test" + LS + "2\n"
    wanted = "hallo TEST ONE"

#########################
# SNIPPETS FILE PARSING #
#########################

class ParseSnippets_SimpleSnippet(_VimTest):
    snippets_test_file = ("all", "test_file", r"""
        snippet testsnip "Test Snippet" b!
        This is a test snippet!
        endsnippet
        """)
    keys = "testsnip" + EX
    wanted = "This is a test snippet!"

class ParseSnippets_MissingEndSnippet(_VimTest):
    snippets_test_file = ("all", "test_file", r"""
        snippet testsnip "Test Snippet" b!
        This is a test snippet!
        """)
    keys = "testsnip" + EX
    wanted = "testsnip" + EX
    expected_error = dedent("""
        UltiSnips: Missing 'endsnippet' for 'testsnip' in test_file(5)
        """).strip()

class ParseSnippets_UnknownDirective(_VimTest):
    snippets_test_file = ("all", "test_file", r"""
        unknown directive
        """)
    keys = "testsnip" + EX
    wanted = "testsnip" + EX
    expected_error = dedent("""
        UltiSnips: Invalid line 'unknown directive' in test_file(2)
        """).strip()

class ParseSnippets_ExtendsWithoutFiletype(_VimTest):
    snippets_test_file = ("all", "test_file", r"""
        extends
        """)
    keys = "testsnip" + EX
    wanted = "testsnip" + EX
    expected_error = dedent("""
        UltiSnips: 'extends' without file types in test_file(2)
        """).strip()

class ParseSnippets_ClearAll(_VimTest):
    snippets_test_file = ("all", "test_file", r"""
        snippet testsnip "Test snippet"
        This is a test.
        endsnippet

        clearsnippets
        """)
    keys = "testsnip" + EX
    wanted = "testsnip" + EX

class ParseSnippets_ClearOne(_VimTest):
    snippets_test_file = ("all", "test_file", r"""
        snippet testsnip "Test snippet"
        This is a test.
        endsnippet

        snippet toclear "Snippet to clear"
        Do not expand.
        endsnippet

        clearsnippets toclear
        """)
    keys = "toclear" + EX + "\n" + "testsnip" + EX
    wanted = "toclear" + EX + "\n" + "This is a test."

class ParseSnippets_ClearTwo(_VimTest):
    snippets_test_file = ("all", "test_file", r"""
        snippet testsnip "Test snippet"
        This is a test.
        endsnippet

        snippet toclear "Snippet to clear"
        Do not expand.
        endsnippet

        clearsnippets testsnip toclear
        """)
    keys = "toclear" + EX + "\n" + "testsnip" + EX
    wanted = "toclear" + EX + "\n" + "testsnip" + EX


###########################################################################
#                               END OF TEST                               #
###########################################################################
if __name__ == '__main__':
    import sys
    import optparse

    def parse_args():
        p = optparse.OptionParser("%prog [OPTIONS] <test case names to run>")

        p.set_defaults(session="vim", interrupt=False, verbose=False)

        p.add_option("-v", "--verbose", dest="verbose", action="store_true",
            help="print name of tests as they are executed")
        p.add_option("-s", "--session", dest="session",  metavar="SESSION",
            help="send commands to screen session SESSION [%default]")
        p.add_option("-i", "--interrupt", dest="interrupt",
            action="store_true",
            help="Stop after defining the snippet. This allows the user" \
             "to interactively test the snippet in vim. You must give exactly" \
            "one test case on the cmdline. The test will always fail."
        )

        o, args = p.parse_args()
        return o, args

    options,selected_tests = parse_args()

    # The next line doesn't work in python 2.3
    test_loader = unittest.TestLoader()
    all_test_suites = test_loader.loadTestsFromModule(__import__("test"))

    # Ensure we are not running in VI-compatible mode.
    send(""":set nocompatible\n""", options.session)

    # Ensure runtimepath includes only Vim's own runtime files
    # and those of the UltiSnips directory under test ('.').
    send(""":set runtimepath=$VIMRUNTIME,.\n""", options.session)

    # Set the options
    send(""":let g:UltiSnipsExpandTrigger="<tab>"\n""", options.session)
    send(""":let g:UltiSnipsJumpForwardTrigger="?"\n""", options.session)
    send(""":let g:UltiSnipsJumpBackwardTrigger="+"\n""", options.session)
    send(""":let g:UltiSnipsListSnippets="@"\n""", options.session)

    # Now, source our runtime
    send(":so plugin/UltiSnips.vim\n", options.session)

    # Inform all test case which screen session to use
    suite = unittest.TestSuite()
    for s in all_test_suites:
        for test in s:
            test.session = options.session
            test.interrupt = options.interrupt
            if len(selected_tests):
                id = test.id().split('.')[1]
                if not any([ id.startswith(t) for t in selected_tests ]):
                    continue
            suite.addTest(test)


    if options.verbose:
        v = 2
    else:
        v = 1
    res = unittest.TextTestRunner(verbosity=v).run(suite)

