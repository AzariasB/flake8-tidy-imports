import ast
import sys
from typing import Any, Dict, Generator, Set, Tuple, Type

from flake8.options.manager import OptionManager

if sys.version_info >= (3, 8):
    from importlib.metadata import version
else:
    from importlib_metadata import version


class ImportChecker:
    """
    Flake8 plugin to make your import statements tidier.
    """

    name = "flake8-tidy-imports"
    version = version("flake8-tidy-imports")

    banned_modules: Dict[str, str]
    ban_relative_imports: bool

    def __init__(self, tree: ast.AST) -> None:
        self.tree = tree

    @classmethod
    def add_options(cls, parser: OptionManager) -> None:
        parser.add_option(
            "--banned-modules",
            action="store",
            parse_from_config=True,
            default="",
            help=(
                "A map of modules to ban to the error messages to "
                + "display in the error."
            ),
        )

        parser.add_option(
            "--ban-relative-imports",
            action="store",
            nargs="?",
            const="true",
            parse_from_config=True,
            choices=["", "non-peers", "true"],
            default="",
            help="Ban relative imports (use absolute imports instead).",
        )

    @classmethod
    def parse_options(cls, options: Any) -> None:
        lines = [
            line.strip() for line in options.banned_modules.split("\n") if line.strip()
        ]
        cls.banned_modules = {}
        for line in lines:
            if line == "{python2to3}":
                cls.banned_modules.update(cls.python2to3_banned_modules)
                continue
            if "=" not in line:
                raise ValueError("'=' not found")
            module, message = line.split("=", 1)
            module = module.strip()
            message = message.strip()
            cls.banned_modules[module] = message

        cls.ban_relative_imports = options.ban_relative_imports

    message_I250 = "I250 Unnecessary import alias - rewrite as '{}'."
    message_I251 = "I251 Banned import '{name}' used - {msg}."
    message_I252 = "I252 Relative imports are banned."

    def run(self) -> Generator[Tuple[int, int, str, Type[Any]], None, None]:
        rule_funcs = (self.rule_I250, self.rule_I251, self.rule_I252)
        for node in ast.walk(self.tree):
            for rule_func in rule_funcs:
                yield from rule_func(node)

    def rule_I250(
        self, node: ast.AST
    ) -> Generator[Tuple[int, int, str, Type[Any]], None, None]:
        if isinstance(node, ast.Import):
            for alias in node.names:

                if "." not in alias.name:
                    from_name = None
                    imported_name = alias.name
                else:
                    from_name, imported_name = alias.name.rsplit(".", 1)

                if imported_name == alias.asname:

                    if from_name:
                        rewritten = f"from {from_name} import {imported_name}"
                    else:
                        rewritten = f"import {imported_name}"

                    yield (
                        node.lineno,
                        node.col_offset,
                        self.message_I250.format(rewritten),
                        type(self),
                    )
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == alias.asname:

                    rewritten = f"from {node.module} import {alias.name}"

                    yield (
                        node.lineno,
                        node.col_offset,
                        self.message_I250.format(rewritten),
                        type(self),
                    )

    def rule_I251(
        self, node: ast.AST
    ) -> Generator[Tuple[int, int, str, Type[Any]], None, None]:
        if isinstance(node, ast.Import):
            module_names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            node_module = node.module or ""
            module_names = [node_module]
            for alias in node.names:
                module_names.append(f"{node_module}.{alias.name}")
        else:
            return

        # Sort from most to least specific paths.
        module_names.sort(key=len, reverse=True)

        warned: Set[str] = set()

        for module_name in module_names:

            if module_name in self.banned_modules:
                message = self.message_I251.format(
                    name=module_name, msg=self.banned_modules[module_name]
                )
                if any(mod.startswith(module_name) for mod in warned):
                    # Do not show an error for this line if we already showed
                    # a more specific error.
                    continue
                else:
                    warned.add(module_name)
                yield (node.lineno, node.col_offset, message, type(self))

    def rule_I252(
        self, node: ast.AST
    ) -> Generator[Tuple[int, int, str, Type[Any]], None, None]:
        if self.ban_relative_imports == "non-peers":
            min_node_level = 1
        else:
            min_node_level = 0

        if (
            self.ban_relative_imports
            and isinstance(node, ast.ImportFrom)
            and node.level > min_node_level
        ):
            yield (node.lineno, node.col_offset, self.message_I252, type(self))

    python2to3_banned_modules = {
        "__builtin__": "use six.moves.builtins as a drop-in replacement",
        "_winreg": "use six.moves.winreg as a drop-in replacement",
        "anydbm": "use dbm as a drop-in replacement",
        "asynchat.fifo": "removed in Python 3",
        "audiodev": "removed in Python 3",
        "BaseHTTPServer": "use six.moves.BaseHTTPServer as a drop-in replacement",
        "Bastion": "removed in Python 3",
        "bsddb185": "use bsddb3 instead",
        "Canvas": "removed in Python 3",
        "cfmfile": "removed in Python 3",
        "CGIHTTPServer": "use six.moves.CGIHTTPServer as a drop-in replacement",
        "cl": "removed in Python 3",
        "commands": "removed in Python 3, use subprocess instead",
        "compiler": "removed in Python 3, use ast instead",
        "ConfigParser": "use six.moves.configparser as a drop-in replacement",
        "contextlib.nested": "use contextlib2.ExitStack or the shim in http://stackoverflow.com/a/39158985/303931",  # noqa:B950
        "Cookie": "use six.moves.http_cookies as a drop-in replacement",
        "cookielib": "use six.moves.http_cookiejar as a drop-in replacement",
        "copy_reg": "use six.moves.copyreg as a drop-in replacement",
        "cPickle": "use six.moves.cPickle as a drop-in replacement",
        "cStringIO": "moved in Python 3, use io.StringIO or io.BytesIO instead",
        "Dialog": "use six.moves.tkinter_dialog as a drop-in replacement",
        "dircache": "removed in Python 3",
        "dl": "removed in Python 3, use ctypes instead",
        "DocXMLRPCServer": "use six.moves.xmlrpc_server instead",
        "dummy_thread": "use six.moves._dummy_thread as a drop-in replacement",
        "email.MIMEBase": "use six.moves.email_mime_base as a drop-in replacement",
        "email.MIMEMultipart": "use six.moves.email_mime_multipart as a drop-in replacement",  # noqa:B950
        "email.MIMENonMultipart": "use six.moves.email_mime_nonmultipart as a drop-in replacement",  # noqa:B950
        "email.MIMEText": "use six.moves.email_mime_text as a drop-in replacement",
        "FileDialog": "use six.moves.tkinter_filedialog as a drop-in replacement",
        "fpformat": "removed in Python 3",
        "ftplib.Netrc": "removed in Python 3",
        "functools.wraps": "use six.wraps as a drop-in replacement",
        "gdbm": "use six.moves.dbm_gnu as a drop-in replacement",
        "htmlentitydefs": "use six.moves.html_entities as a drop-in replacement",
        "htmllib": "use six.moves.html_parser instead",
        "HTMLParser": "use six.moves.html_parser as a drop-in replacement (except for HTMLParserError)",  # noqa:B950
        "HTMLParser.HTMLParseError": "removed in Python 3.5+",
        "httplib": "use six.moves.http_client as a drop-in replacement",
        "ihooks": "removed in Python 3",
        "imageop": "removed in Python 3, use PIL/Pillow instead",
        "imputil": "removed in Python 3",
        "inspect.getmoduleinfo": "moved in Python 3, use inspect.getmodulename instead",
        "itertools.ifilter": "use six.moves.filter as a drop-in replacement",
        "itertools.ifilterfalse": "use six.moves.filterfalse as a drop-in replacement",
        "itertools.imap": "use six.moves.map as a drop-in replacement",
        "itertools.izip": "use six.moves.zip as a drop-in replacement",
        "itertools.izip_longest": "use six.moves.zip_longest as a drop-in replacement",
        "linuxaudiodev": "moved in Python 3, use ossaudiodev instead",
        "markupbase": "moved in Python 3, use _markupbase instead",
        "md5": "removed in Python 3, use hashlib.md5() instead",
        "mhlib": "removed in Python 3, use mailbox instead",
        "mimetools": "moved in Python 3, use email instead",
        "MimeWriter": "moved in Python 3, use email instead",
        "mimify": "removed in Python 3, use email instead",
        "multifile": "removed in Python 3, use email instead",
        "mutex": "removed in Python 3",
        "new": "removed in Python 3",
        "os.getcwd": "use six.moves.getcwdb as a drop-in replacement",
        "os.getcwdu": "use six.moves.getcwd as a drop-in replacement",
        "pipes.quote": "use six.moves.shlex_quote as a drop-in replacement",
        "platform._bcd2str": "removed in Python 3",
        "platform._mac_ver_gstalt": "removed in Python 3",
        "platform._mac_ver_lookup": "removed in Python 3",
        "plistlib.readPlist": "moved in Python 3, use plistlib.load instead",
        "plistlib.readPlistFromBytes": "moved in Python 3, use plistlib.loads instead",
        "plistlib.writePlist": "moved in Python 3, use plistlib.dump instead",
        "plistlib.writePlistToBytes": "moved in Python 3, use plistlib.dumps instead",
        "popen2": "moved in Python 3, use subprocess instead",
        "posixfile": "moved in Python 3, use fcntl.lockf instead",
        "pure": "removed in Python 3",
        "pydoc.Scanner": "removed in Python 3",
        "Queue": "use six.moves.queue as a drop-in replacement",
        "repr": "use six.moves.reprlib as a drop-in replacement",
        "rexec": "removed in Python 3",
        "rfc822": "moved in Python 3, use email instead",
        "robotparser": "use six.moves.urllib.robotparser as a drop-in replacement",
        "ScrolledText": "use six.moves.tkinter_scrolledtext as a drop-in replacement",
        "sgmllib": "removed in Python 3",
        "sha": "moved in Python 3, use hashlib.sha1() instead",
        "SimpleDialog": "use six.moves.tkinter_simpledialog as a drop-in replacement",
        "SimpleHTTPServer": "use six.moves.SimpleHTTPServer as a drop-in replacement",
        "SimpleXMLRPCServer": "use six.moves.xmlrpc_server as a drop-in replacement",
        "smtplib.SSLFakeFile": "moved in Python 3, use socket.socket.makefile instead",
        "SocketServer": "use six.moves.socketserver as a drop-in replacement",
        "sre": "moved in Python 3, use re instead",
        "statvfs": "moved in Python 3, use os.statvfs instead",
        "string.atof": "moved in Python 3, use float() as a drop-in replacement",
        "string.atoi": "moved in Python 3. use int() as a drop-in replacement",
        "string.atol": "moved in Python 3. use int() as a drop-in replacement",
        "string.capitalize": "removed in Python 3",
        "string.center": "removed in Python 3",
        "string.count": "removed in Python 3",
        "string.expandtabs": "removed in Python 3",
        "string.find": "removed in Python 3",
        "string.index": "removed in Python 3",
        "string.join": "removed in Python 3",
        "string.joinfields": "removed in Python 3",
        "string.letters": "moved in Python 3, use string.ascii_letters as a drop-in replacement",  # noqa:B950
        "string.ljust": "removed in Python 3",
        "string.lower": "removed in Python 3",
        "string.lowercase": "moved in Python 3, use string.ascii_lowercase as a drop-in replacement",  # noqa:B950
        "string.lstrip": "removed in Python 3",
        "string.maketrans": "moved in Python 3, use bytes.maketrans/bytearray.maketrans or a dict of unicode codepoints to substitutions instead",  # noqa:B950
        "string.replace": "removed in Python 3",
        "string.rfind": "removed in Python 3",
        "string.rindex": "removed in Python 3",
        "string.rjust": "removed in Python 3",
        "string.rsplit": "removed in Python 3",
        "string.rstrip": "removed in Python 3",
        "string.split": "removed in Python 3",
        "string.splitfields": "removed in Python 3",
        "string.strip": "removed in Python 3",
        "string.swapcase": "removed in Python 3",
        "string.translate": "removed in Python 3",
        "string.upper": "removed in Python 3",
        "string.uppercase": "moved in Python 3, use string.ascii_uppercase as a drop-in replacement",  # noqa:B950
        "string.zfill": "removed in Python 3",
        "StringIO": "moved in Python 3, use io.StringIO or io.BytesIO instead",
        "stringold": "removed in Python 3",
        "sunaudio": "removed in Python 3",
        "sv": "removed in Python 3",
        "tarfile.S_IFBLK": "moved in Python 3, use stat.S_IFBLK as a drop-in replacement",  # noqa:B950
        "tarfile.S_IFCHR": "moved in Python 3, use stat.S_IFCHR as a drop-in replacement",  # noqa:B950
        "tarfile.S_IFDIR": "moved in Python 3, use stat.S_IFDIR as a drop-in replacement",  # noqa:B950
        "tarfile.S_IFIFO": "moved in Python 3, use stat.S_IFIFO as a drop-in replacement",  # noqa:B950
        "tarfile.S_IFLNK": "moved in Python 3, use stat.S_IFLNK as a drop-in replacement",  # noqa:B950
        "tarfile.S_IFREG": "moved in Python 3, use stat.S_IFREG as a drop-in replacement",  # noqa:B950
        "test.test_support": "moved in Python 3, use test.support instead",
        "test.testall": "removed in Python 3",
        "thread": "moved in Python 3, use six.moves._thread as a drop-in replacement",
        "time.accept2dyear": "removed in Python 3",
        "timing": "moved in Python 3, use time.clock instead",
        "Tix": "use six.moves.tkinter_tix as a drop-in replacement",
        "tkColorChooser": "use six.moves.tkinter_colorchooser as a drop-in replacement",
        "tkCommonDialog": "use six.moves.tkinter_commondialog as a drop-in replacement",
        "Tkconstants": "use six.moves.tkinter_constants as a drop-in replacement",
        "Tkdnd": "use six.moves.tkinter_dnd as a drop-in replacement",
        "tkFileDialog": "use six.moves.tkinter_tkfiledialog as a drop-in replacement",
        "tkFont": "use six.moves.tkinter_font as a drop-in replacement",
        "Tkinter": "use six.moves.tkinter as a drop-in replacement",
        "tkMessageBox": "use six.moves.tkinter_messagebox as a drop-in replacement",
        "tkSimpleDialog": "use six.moves.tkinter_tksimpledialog as a drop-in replacement",  # noqa:B950
        "toaiff": "removed in Python 3",
        "ttk": "use six.moves.tkinter_ttk as a drop-in replacement",
        "types.BooleanType": "moved in Python 3, use bool as a drop-in replacement",
        "types.BufferType": "removed in Python 3",
        "types.ClassType": "removed in Python 3",
        "types.ComplexType": "moved in Python 3, use complex as a drop-in replacement",
        "types.DictionaryType": "removed in Python 3",
        "types.DictProxyType": "removed in Python 3",
        "types.DictType": "moved in Python 3, use dict as a drop-in replacement",
        "types.EllipsisType": "moved in Python 3, use type(Ellipsis) as a drop-in replacement",  # noqa:B950
        "types.FileType": "removed in Python 3",
        "types.FloatType": "moved in Python 3, use float as a drop-in replacement",
        "types.InstanceType": "removed in Python 3",
        "types.IntType": "use six.integer_types as a drop-in replacement",
        "types.ListType": "moved in Python 3, use list as a drop-in replacement",
        "types.LongType": "removed in Python 3",
        "types.NoneType": "moved in Python 3, use type(None) as a drop-in replacement",
        "types.NotImplementedType": "removed in Python 3",
        "types.ObjectType": "removed in Python 3",
        "types.SliceType": "removed in Python 3",
        "types.StringType": "use six.binary_types or six.text_types, depending on context, instead",  # noqa:B950
        "types.StringTypes": "use six.string_types as a drop-in replacement",
        "types.TupleType": "moved in Python 3, use tuple as a drop-in replacement",
        "types.TypeType": "use six.class_types as a drop-in replacement",
        "types.UnboundMethodType": "removed in Python 3",
        "types.UnicodeType": "use six.text_type as a drop-in replacement",
        "types.XRangeType": "removed in Python 3",
        "urllib.ContentTooShortError": "use six.moves.urllib.error.ContentTooShortError as a drop-in replacement",  # noqa:B950
        "urllib.FancyURLopener": "use six.moves.urllib.request.FancyURLopener as a drop-in replacement",  # noqa:B950
        "urllib.getproxies": "use six.moves.urllib.request.getproxies as a drop-in replacement",  # noqa:B950
        "urllib.pathname2url": "use six.moves.urllib.request.pathname2url as a drop-in replacement",  # noqa:B950
        "urllib.proxy_bypass": "use six.moves.urllib.request.proxy_bypass as a drop-in replacement",  # noqa:B950
        "urllib.quote": "use six.moves.urllib.parse.quote as a drop-in replacement",
        "urllib.quote_plus": "use six.moves.urllib.parse.quote_plus as a drop-in replacement",  # noqa:B950
        "urllib.splitattr": "moved in Python 3, use urllib.parse.splitattr instead",
        "urllib.splithost": "moved in Python 3, use urllib.parse.splithost instead",
        "urllib.splitnport": "moved in Python 3, use urllib.parse.splitnport instead",
        "urllib.splitpasswd": "moved in Python 3, use urllib.parse.splitpasswd instead",
        "urllib.splitport": "moved in Python 3, use urllib.parse.splitport instead",
        "urllib.splitquery": "use six.moves.urllib.parse.splitquery as a drop-in replacement",  # noqa:B950
        "urllib.splittag": "use six.moves.urllib.parse.splittag as a drop-in replacement",  # noqa:B950
        "urllib.splittype": "moved in Python 3, use urllib.parse.splittype instead",
        "urllib.splituser": "use six.moves.urllib.parse.splituser as a drop-in replacement",  # noqa:B950
        "urllib.splitvalue": "moved in Python 3, use urllib.parse.splitvalue instead",
        "urllib.unquote": "use six.moves.urllib.parse.unquote as a drop-in replacement",
        "urllib.unquote_plus": "use six.moves.urllib.parse.unquote_plus as a drop-in replacement",  # noqa:B950
        "urllib.url2pathname": "use six.moves.urllib.request.url2pathname as a drop-in replacement",  # noqa:B950
        "urllib.urlcleanup": "use six.moves.urllib.request.urlcleanup as a drop-in replacement",  # noqa:B950
        "urllib.urlencode": "use six.moves.urllib.parse.urlencode as a drop-in replacement",  # noqa:B950
        "urllib.URLopener": "use six.moves.urllib.request.URLopener as a drop-in replacement",  # noqa:B950
        "urllib.urlretrieve": "use six.moves.urllib.request.urlretrieve as a drop-in replacement",  # noqa:B950
        "urllib2": "use six.moves.urllib instead",
        "urllib2.AbstractBasicAuthHandler": "use six.moves.urllib.request.AbstractBasicAuthHandler as a drop-in replacement",  # noqa:B950
        "urllib2.AbstractDigestAuthHandler": "use six.moves.urllib.request.AbstractDigestAuthHandler as a drop-in replacement",  # noqa:B950
        "urllib2.BaseHandler": "use six.moves.urllib.request.BaseHandler as a drop-in replacement",  # noqa:B950
        "urllib2.build_opener": "use six.moves.urllib.request.build_opener as a drop-in replacement",  # noqa:B950
        "urllib2.CacheFTPHandler": "use six.moves.urllib.request.CacheFTPHandler as a drop-in replacement",  # noqa:B950
        "urllib2.FileHandler": "use six.moves.urllib.request.FileHandler as a drop-in replacement",  # noqa:B950
        "urllib2.FTPHandler": "use six.moves.urllib.request.FTPHandler as a drop-in replacement",  # noqa:B950
        "urllib2.HTTPBasicAuthHandler": "use six.moves.urllib.request.HTTPBasicAuthHandler as a drop-in replacement",  # noqa:B950
        "urllib2.HTTPCookieProcessor": "use six.moves.urllib.request.HTTPCookieProcessor as a drop-in replacement",  # noqa:B950
        "urllib2.HTTPDefaultErrorHandler": "use six.moves.urllib.request.HTTPDefaultErrorHandler as a drop-in replacement",  # noqa:B950
        "urllib2.HTTPDigestAuthHandler": "use six.moves.urllib.request.HTTPDigestAuthHandler as a drop-in replacement",  # noqa:B950
        "urllib2.HTTPError": "use six.moves.urllib.error.HTTPError as a drop-in replacement",  # noqa:B950
        "urllib2.HTTPErrorProcessor": "use six.moves.urllib.request.HTTPErrorProcessor as a drop-in replacement",  # noqa:B950
        "urllib2.HTTPHandler": "use six.moves.urllib.request.HTTPHandler as a drop-in replacement",  # noqa:B950
        "urllib2.HTTPPasswordMgr": "use six.moves.urllib.request.HTTPPasswordMgr as a drop-in replacement",  # noqa:B950
        "urllib2.HTTPPasswordMgrWithDefaultRealm": "use six.moves.urllib.request.HTTPPasswordMgrWithDefaultRealm as a drop-in replacement",  # noqa:B950
        "urllib2.HTTPRedirectHandler": "use six.moves.urllib.request.HTTPRedirectHandler as a drop-in replacement",  # noqa:B950
        "urllib2.HTTPSHandler": "use six.moves.urllib.request.HTTPSHandler as a drop-in replacement",  # noqa:B950
        "urllib2.install_opener": "use six.moves.urllib.request.install_opener as a drop-in replacement",  # noqa:B950
        "urllib2.OpenerDirector": "use six.moves.urllib.request.OpenerDirector as a drop-in replacement",  # noqa:B950
        "urllib2.ProxyBasicAuthHandler": "use six.moves.urllib.request.ProxyBasicAuthHandler as a drop-in replacement",  # noqa:B950
        "urllib2.ProxyDigestAuthHandler": "use six.moves.urllib.request.ProxyDigestAuthHandler as a drop-in replacement",  # noqa:B950
        "urllib2.ProxyHandler": "use six.moves.urllib.request.ProxyHandler as a drop-in replacement",  # noqa:B950
        "urllib2.quote": "use six.moves.urllib.parse.quote as a drop-in replacement",
        "urllib2.Request": "use six.moves.urllib.request.Request as a drop-in replacement",  # noqa:B950
        "urllib2.UnknownHandler": "use six.moves.urllib.request.UnknownHandler as a drop-in replacement",  # noqa:B950
        "urllib2.unquote": "use six.moves.urllib.parse.unquote as a drop-in replacement",  # noqa:B950
        "urllib2.URLError": "use six.moves.urllib.error.URLError as a drop-in replacement",  # noqa:B950
        "urllib2.urlopen": "use six.moves.urllib.request.urlopen as a drop-in replacement",  # noqa:B950
        "urlparse": "use six.moves.urllib.parse as a drop-in replacement",
        "urlparse.scheme_chars": "moved in Python 3, use urllib.parse.scheme_chars",
        "user": "removed in Python 3",
        "UserDict": "moved in Python 3, use dict or collections.UserDict/collections.MutableMapping instead",  # noqa:B950
        "UserDict.UserDict": "moved in Python 3, use six.moves.UserDict as a drop-in replacement",  # noqa:B950
        "UserDict.UserDictMixin": "moved in Python 3, use collections.MutableMapping instead",  # noqa:B950
        "UserList": "moved in Python 3, use list or collections.UserList/collections.MutableSequence instead",  # noqa:B950
        "UserList.UserList": "use six.moves.UserList as a drop-in replacement",
        "UserString": "moved in Python 3, use six.text_type, six.binary_type or collections.UserString instead",  # noqa:B950
        "UserString.UserString": "use six.moves.UserString as a drop-in replacement",
        "xmlrpclib": "use six.moves.xmlrpc_client as a drop-in replacement",
    }
