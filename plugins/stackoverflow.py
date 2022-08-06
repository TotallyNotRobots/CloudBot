# Search for answers on stackoverflow
# Author: Matheus Fillipe
# Date: 03/08/2022
# Based on https://github.com/drathier/stack-overflow-import/blob/master/stackoverflow/__init__.py


import ast
import html
import re
from cloudbot.util.queue import Queue
from dataclasses import dataclass

import requests

from cloudbot import hook

API_URL = "https://api.stackexchange.com"
TAGS = {"javascript", "python", "java", "c#", "php", "android", "html", "jquery", "c++", "css", "ios", "mysql", "sql", "r", "node.js", "reactjs", "arrays", "c", "asp.net", "json", "ruby-on-rails", ".net", "sql-server", "python-3.x", "swift", "django", "objective-c", "angular", "excel", "angularjs", "pandas", "regex", "ruby", "iphone", "ajax", "linux", "xml", "vba", "spring", "asp.net-mvc", "laravel", "typescript", "database", "wordpress", "string", "wpf", "mongodb", "windows", "postgresql", "xcode", "bash", "oracle", "git", "amazon-web-services", "vb.net", "multithreading", "flutter", "list", "firebase", "spring-boot", "dataframe", "eclipse", "azure", "react-native", "docker", "algorithm", "macos", "forms", "image", "visual-studio", "scala", "powershell", "numpy", "function", "twitter-bootstrap", "api", "selenium", "performance", "winforms", "vue.js", "python-2.7", "matlab", "sqlite", "hibernate", "apache", "loops", "entity-framework", "rest", "shell", "express", "android-studio", "facebook", "csv", "linq", "maven", "qt", "unit-testing", "swing", "file", "tensorflow", "kotlin", "class", "apache-spark", "dart", "date", "sorting", "dictionary", ".htaccess", "asp.net-core", "symfony", "tsql", "google-chrome", "codeigniter", "opencv", "perl", "for-loop", "unity3d", "datetime", "matplotlib", "http", "google-maps", "validation", "sockets", "uitableview", "go", "object", "cordova", "web-services", "xaml", "oop", "android-layout", "if-statement", "email", "ubuntu", "spring-mvc", "ruby-on-rails-3", "ms-access", "c++11", "parsing", "elasticsearch", "authentication", "security", "user-interface", "pointers", "sql-server-2008", "templates", "batch-file", "jsp", "variables", "listview", "nginx", "github", "machine-learning", "flask", "wcf", "debugging", "delphi", "kubernetes", "haskell", "jpa", "xamarin", "ssl", "ggplot2", "pdf", "asynchronous", "jenkins", "selenium-webdriver", "gradle", "visual-studio-code", "google-apps-script", "testing", "visual-studio-2010", "tkinter", "generics", "unix", "google-app-engine", "amazon-s3", "web", "npm", "google-sheets", "android-fragments", "ionic-framework", "recursion", "web-scraping", "session", "hadoop", "mongoose", "heroku", "animation", "url", "asp.net-mvc-4", "tomcat", "curl", "math", "svg", "actionscript-3", "exception", "join", "assembly", "inheritance", "intellij-idea", "winapi", "webpack", "django-models", "image-processing", "keras", "dom", ".net-core", "post", "jquery-ui", "google-cloud-platform", "cocoa", "matrix", "redirect", "logging", "gcc", "internet-explorer", "button", "d3.js", "asp.net-mvc-3", "firebase-realtime-database", "select", "firefox", "laravel-5", "magento", "iis", "xpath", "opengl", "xslt", "networking", "events", "javafx", "optimization", "caching", "ruby-on-rails-4", "asp.net-web-api", "search", "google-cloud-firestore", "stored-procedures", "encryption", "jsf", "plot", "flash", "canvas", "audio", "facebook-graph-api", "ipad", "memory", "cocoa-touch", "amazon-ec2", "multidimensional-array", "vector", "redux", "arraylist", "cookies", "random", "pyspark", "input", "video", "servlets", "xamarin.forms", "model-view-controller", "mod-rewrite", "indexing", "jdbc", "serialization", "razor", "data-structures", "iframe", "cakephp", "dplyr", "awk", "woocommerce", "design-patterns", "android-intent", "visual-c++", "text", "rust", "grails", "filter", "beautifulsoup", "mobile", "jakarta-ee", "methods", "ecmascript-6", "checkbox", "meteor", "struct", "mvvm", "android-activity", "groovy", "core-data", "django-rest-framework", "time", "ssh", "android-recyclerview", "lambda", "apache-kafka", "installation", "sharepoint", "activerecord", "bootstrap-4", "google-chrome-extension", "vim", "graph", "sed", "soap", "swiftui", "file-upload", "silverlight", "plsql", "excel-formula", "boost", "aws-lambda", "junit", "svn", "gridview", "memory-management", "azure-devops", "replace", "dynamic", "types", "scikit-learn", "websocket", "layout", "spring-security", "docker-compose", "shiny", "browser", "c#-4.0", "import", "sass", "cmd", "charts", "dll", "eloquent", "error-handling", "cmake", "vuejs2", "mysqli", "dependency-injection", "reporting-services", "google-maps-api-3", "deep-learning", "twitter", "while-loop", "plugins", "foreach", "extjs", "ffmpeg", "highcharts", "group-by", "unicode", "reflection", "https", "deployment", "async-await", "apache-flex", "makefile", "netbeans", "ember.js", "server", "pdo", "database-design", "encoding", "merge", "hash", "collections", "data-binding", "react-hooks", "visual-studio-2012", "redis", "command-line", "terminal", "jquery-mobile", "split", "service", "printing", "java-8", "html-table", "tcp", "react-redux", "django-views", "web-applications", "neo4j", "webview", "build", "utf-8", "uwp", "automation", "tfs", "promise", "oauth-2.0", "datatable", "google-bigquery", "twitter-bootstrap-3", "concurrency", "module", "drop-down-menu", "hive", "enums", "scroll", "sqlalchemy", "pip", "view", "axios", "apache-spark-sql", "file-io", "gwt", "syntax", "parameters", "ansible", "colors", "backbone.js", "outlook", "paypal", "lua", "ssis", "google-analytics", "count", "zend-framework", "jestjs", "jupyter-notebook", "next.js", "constructor", "fonts", "knockout.js", "solr", "drupal", "parallel-processing", "flexbox", "spring-data-jpa", "datagridview", "oracle11g", "socket.io", "python-requests", "graphics", "scipy", "windows-phone-7", "ms-word", "parse-platform", "visual-studio-2015", "memory-leaks", "firebase-authentication", "three.js", "cassandra", "oauth", "interface", "compiler-errors", "primefaces", "rxjs", "timer", "neural-network", "django-forms", "pygame", "casting", "proxy", "linked-list", "directory", "visual-studio-2013", "triggers", "google-api", "graphql", "orm", "datatables", "react-router", "uiview", "vbscript", "routes", "nlp", "arduino", "material-ui", "jar", "push-notification", "sql-server-2005", "swift3", "path", "windows-phone-8", "model", "django-templates", "functional-programming", "xamarin.android", "hyperlink", "pytorch", "login", "entity-framework-core", "rspec", "discord", "download", "angular-material", "combobox", "process", "properties", "jmeter", "callback", "angularjs-directive", "emacs", "nhibernate", "configuration", "clojure", "cron", "playframework",
        "safari", "io", "scripting", "pagination", "scope", "doctrine-orm", "sql-server-2012", "dns", "scrapy", "permissions", "raspberry-pi", "version-control", "binding", "yii", "responsive-design", "url-rewriting", "linux-kernel", "bluetooth", "compilation", "get", "kendo-ui", "request", "3d", "architecture", "reference", "f#", "autocomplete", "datepicker", "xamarin.ios", "uiviewcontroller", "pyqt", "tree", "controller", "phpmyadmin", "x86", "mongodb-query", "static", "grep", "jsf-2", "nullpointerexception", "datagrid", "visual-studio-2008", "webforms", "asp.net-mvc-5", "google-cloud-functions", "jackson", "android-listview", "null", "menu", "bitmap", "transactions", "notifications", "youtube", "nested", "active-directory", "openssl", "discord.js", "ant", "pycharm", "azure-active-directory", "yii2", "statistics", "stl", "gitlab", "joomla", "stream", "powerbi", "jboss", "devise", "jwt", "character-encoding", "linq-to-sql", "ios7", "mocking", "hashmap", "sas", "computer-vision", "android-asynctask", "msbuild", "sum", "background", "laravel-4", "sdk", "floating-point", "css-selectors", "camera", "exception-handling", "cryptography", "onclick", "binary", "uicollectionview", "duplicates", "insert", "ftp", "time-series", "routing", "tabs", "opengl-es", "electron", "coldfusion", "textview", "terraform", "google-drive-api", "xsd", "upload", "navigation", "anaconda", "iterator", "cuda", "pyqt5", "xml-parsing", "console", "rabbitmq", "linker", "android-ndk", "discord.py", "localization", "yaml", "multiprocessing", "calendar", "sprite-kit", "leaflet", "header", "jquery-plugins", "json.net", "operating-system", "dockerfile", "asp.net-core-mvc", "formatting", "jasmine", "prolog", "macros", "timestamp", "drag-and-drop", "continuous-integration", "package", "type-conversion", "crash", "azure-functions", "segmentation-fault", "char", "mfc", "kivy", "selenium-chromedriver", "data.table", "annotations", "visual-studio-2017", "nosql", "mockito", "gulp", "mariadb", "integer", "attributes", "libgdx", "textbox", "android-gradle-plugin", "uiscrollview", "amazon-dynamodb", "environment-variables", "fortran", "crystal-reports", "automated-tests", "geometry", "centos", "keyboard", "xampp", "format", "db2", "flutter-layout", "event-handling", "cors", "ionic2", "frontend", "mapreduce", "geolocation", "com", "namespaces", "android-edittext", "dependencies", "windows-10", "dialog", "android-emulator", "lucene", "ios5", "webdriver", "xmlhttprequest", "jvm", "plotly", "garbage-collection", "rotation", "html5-canvas", "timezone", "radio-button", "expo", "listbox", "numbers", "jenkins-pipeline", "arm", "set", "doctrine", "modal-dialog", "firebase-cloud-messaging", "eclipse-plugin", "smtp", "sql-update", "frameworks", "subprocess", "asp-classic", "wso2", "sonarqube", "http-headers", "compiler-construction", "sequelize.js", "conditional-statements", "struts2", "grid", "ldap", "protractor", "spring-data", "uinavigationcontroller", "sql-server-2008-r2", "aggregation-framework", "widget", "internationalization", "tuples", "serial-port", "switch-statement", "initialization", "rubygems", "uibutton", "boolean", "return", "delegates", "apache-camel", "tags", "microsoft-graph-api", "fetch", "qml", "youtube-api", "windows-7", "nuget", "autolayout", "network-programming", "jaxb", "google-play", "components", "postman", "chart.js", "foreign-keys", "find", "jqgrid", "copy", "swagger", "gdb", "julia", "java-stream", "entity-framework-6", "android-viewpager", "base64", "ios4", "dataset", "uiwebview", "uikit", "queue", "dom-events", "zip", "popup", "ide", "vb6", "azure-web-app-service", "uiimageview", "append", "arguments", "pivot", "composer-php", "stack", "synchronization", "migration", "passwords", "ionic3", "cucumber", "twig", "jersey", "angular-ui-router", "udp", "latex", "command", "windows-8", "gmail", "hover", "cocos2d-iphone", "nuxt.js", "subquery", "gps", "iteration", "user-controls", "containers", "g++", "stripe-payments", "constants", "range", "wix", "google-cloud-storage", "ado.net", "mono", "ssl-certificate", "embedded", "connection", "polymorphism", "vue-component", "jframe", "drupal-7", "imageview", "django-admin", "slider", "compare", "coffeescript", "save", "debian", "int", "label", "sbt", "salesforce", "localhost", "phpunit", "authorization", "certificate", "admob", "local-storage", "c++17", "conv-neural-network", "java-native-interface", "include", "iis-7", "gson", "time-complexity", "log4j", "location", "web-crawler", "itext", "erlang", "r-markdown", "pipe", "clang", "telerik", "output", "timeout", "azure-pipelines", "bots", "fullcalendar", "storyboard", "babeljs", "apache-poi", "twilio", "ios8", "ruby-on-rails-5", "hex", "dojo", "filesystems", "wsdl", "cypher", "treeview", "click", "uiimage", "export", "icons", "ckeditor", "window", "actionscript", "maps", "resources", "ip", "gruntjs", "blazor", "odbc", "substring", "mapping", "observable", "realm", "key", "runtime-error", "thread-safety", "resize", "in-app-purchase", "printf", "cocoapods", "elixir", "cross-browser", "concatenation", "kernel", "botframework", "pandas-groupby", "typo3", "angularjs-scope", "syntax-error", "wordpress-theming", "azure-sql-database", "position", "android-actionbar", "google-visualization", "signalr", "logic", "map", "styles", "imagemagick", ".net-4.0", "compression", "windows-services", "bluetooth-lowenergy", "amazon-elastic-beanstalk", "cloud", "regression", "malloc", "pattern-matching", "ios6", "zend-framework2", "escaping", "jquery-selectors", "jinja2", "repository", "windows-runtime", "webrtc", "seaborn", "pthreads", "command-line-interface", "closures", "windows-installer", "google-sheets-formula", "nestjs", "web-config", "vagrant", "thymeleaf", "max", "google-oauth", "internet-explorer-8", "sharepoint-2010", "tidyverse", "locking", "jtable", "http-post", "asp.net-identity", "swift2", "asp.net-mvc-2", "constraints", "uitextfield", "jasper-reports", "python-imaging-library", "applescript", "global-variables", "ef-code-first", "blackberry", "qt5", "celery", "many-to-many", "airflow", "try-catch", "mocha.js", "alignment", "singleton", "google-chrome-devtools", "video-streaming", "state", "material-design", "pytest", "build.gradle", "controls", "logstash", "testng", "polymer", "language-agnostic", }

results_queue = Queue()


@dataclass
class Question:
    title: str
    url: str
    votes: int
    answers: int
    tags: list

    def __str__(self):
        return self.title


@dataclass
class Answer:
    code: str
    id: str

    def __str__(self):
        return "https://stackoverflow.com/a/" + self.id


def search(query: str, tag: str = None) -> [Question]:
    params = {
        "order": "desc",
        "sort": "relevance",
        "site": "stackoverflow",
        "q": query,
    }

    if tag:
        params.update({"tagged": tag})

    req = requests.get(API_URL + "/search/advanced", params)
    ans = req.json()

    if not ans["items"]:
        return []

    return list(map(lambda i: Question(
        title=html.unescape(i['title']),
        url=i['link'],
        votes=i['score'],
        answers=i['answer_count'],
        tags=i['tags'],
    ),
        ans["items"]
    ))


def find_best_answer_in_html(text: str) -> Answer:
    """Returns the best ranked answer code or none."""
    answers = re.findall(r'(<div id="answer-(\d+)".*?</table)', text,
                         re.DOTALL)

    def votecount(x):
        """Return the negative number of votes a question has.

        Might return the negative question id instead if its less than
        100k. That's a feature.
        """
        r = int(re.search(r"\D(\d{1,5})\D", x[0]).group(1))
        return -r

    for answer in sorted(answers, key=votecount):
        id = answer[1]
        answer = answer[0]
        codez = re.finditer(
            r"<pre[^>]*>[^<]*<code[^>]*>((?:\s|[^<]|<span[^>]*>[^<]+</span>)*)</code></pre>", answer)
        codez = map(lambda x: x.group(1), codez)
        for code in sorted(codez, key=lambda x: -len(x)):  # more code is obviously better
            code = html.unescape(code)
            code = re.sub(r"<[^>]+>([^<]*)<[^>]*>", "\1", code)
            try:
                ast.parse(code)
                return Answer(code, id)
            except Exception:
                pass


def find_best_code(chan, nick) -> (Question, Answer):
    global results_queue
    results = results_queue[chan][nick]
    no_good_code = results_queue[chan][nick].metadata.no_good_code
    if not no_good_code:
        rcopy = list(results)
        for result in rcopy:
            answer = find_best_answer_in_html(requests.get(result.url).text)
            r = results.pop()
            if answer and answer.code:
                return r, answer

        no_good_code = True
        results = rcopy

    if len(results) == 0:
        return None, None
    r = results.pop()
    return r, None


@hook.command("son", autohelp=False)
def sonext(reply, chan, nick, text) -> str:
    """Gets next result in stack overflow and return formated text."""
    global results_queue
    results = results_queue[chan][nick]
    user = text.strip().split()[0] if text.strip() else ""
    if user:
        if user in results_queue[chan]:
            results = results_queue[chan][user]
        else:
            return f"Nick '{user}' has no queue."

    r, answer = find_best_code(chan, nick)
    results = results_queue[chan][nick]
    if len(results) == 0 or r is None:
        return "No [more] results found."

    reply(
        f"\x02{r.title}\x02 - \x02{r.votes}\x02 votes - \x02{r.answers}\x02 answers - {r.tags}")
    reply(f"{r.url}")

    if answer is None:
        return

    lines = [line for line in answer.code.split("\n") if line.strip()]

    for line in lines[:4]:
        reply(line)
    if len(lines) > 4:
        reply(f"... {answer}")
    else:
        reply(f"{answer}")


@hook.command("stackoverflow", "so")
def sosearchhook(text, reply, chan, nick):
    """gitgrep <query> - Searches for <query> in stack overflow returning the first answer with code. If you want a more precise search start the query with a tag (separating words with '-') like 'python' or 'windows-10'"""
    global results_queue
    results = results_queue[chan][nick]
    results.metadata.no_good_code = False
    tag = text.split()[0] if text.split()[0] in TAGS else None
    results.set(search(" ".join(text.split()[1:]), tag))

    if len(results) == 0:
        return "No stackoverflow questions found"

    return sonext(reply, chan, nick, "")
