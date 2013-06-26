
Flipper, a Federated Twitter Clone
==================================

Over the next few lessons, we'll construct a custom web framework and
Twitter clone called Flipper. Flipper will be a minimal Twitter
implementation, but also feature some interesting cross site
communication features. This series of lessons assumes working
knowledge of Python, as well as a familiarity with Linux and the
command line. That said, because of Python's portability, all of this
work could be done on a non-Unix platform.

WSGI
----

The Web Service Gateway Interface (WSGI, pronounced wiz-ghee) is an
interface specification first defined by `PEP 333
<http://www.python.org/dev/peps/pep-0333/>`_, and then later refined
in `PEP 3333 <http://www.python.org/dev/peps/pep-3333/>`_ (read this,
but do not get bogged down in the details). Its purpose is to clarify
the boundary between a web server such as Apache, and the web
application, which contains all of the logic required to take input
from users and return pages to browsers. WSGI is the starting point of
the custom framework you will be develping for this project.

Ben Bangert wrote a quick introduction to WSGI [#]_ and middleware which is
a good starting point:

    http://be.groovie.org/post/296349572/wsgi-and-wsgi-middleware-is-easy

Ben does not mention how to run simple_app from his example. You do
this like so::

    from wsgiref.simple_server import make_server
    httpd = make_server('', 8000, simple_app)
    httpd.serve_forever()

.. note:: Set up simple_app and verify that you can get to it with
   your browser. You should be able to access the page at
   ``localhost:8000`` or your machine's full name.

Constructing an application of any sort of complexity from basic WSGI
would be sisyphean effort. One of the particularly baroque aspects of
WSGI is the ``environ`` variable and ``start_response`` mechanism. A
common method of cleaning up the design is to use response and request
objects instead. You might prefer to write ``simple_app`` like so::

    def simple_app(request):
        """Simplest possible application object"""

        resp = Response()
        resp.status = '200 OK'
        resp.headers = [('Content-type','text/plain')]
        resp.body = 'Hello world!\n'

        return resp

Here, the structure is much more natural: receive a request, processes
it, and return a response. There are several competing implementations
of this design, both within larger frameworks such as `Django
<http://www.djangoproject.com>`_, and as standalone modules, such as
`WebOb <http://pythonpaste.org/webob/>`_ and `Werkzeug
<http://werkzeug.pocoo.org/>`_. We will be using WebOb.

We will now take the standard WSGI function signature and transform it
into something that is WebOb friendly. Recall ``simple_app``::

    def simple_app(environ, start_response):
        """Simplest possible application object"""
        status = '200 OK'
        response_headers = [('Content-type','text/plain')]
        start_response(status, response_headers)
        return ['Hello world!\n']

We would prefer to use Request/Response objects, so this is one
possible transformation::

    def simple_app(environ, start_response):
        """Simplest possible application object"""

        request = webob.Request(environ)

        resp = webob.Response()
        resp.status = '200 OK'
        resp.headers = [('Content-type','text/plain')]
        resp.body = 'Hello world!\n'

        return resp(environ, start_response)

Every WSGI app we write will require a similar transformation. We can
eliminate a little busy work by constructing a decorator::

    def wsgify(webob_app):
        """Take a WebOb friendly app and transform it into a WSGI app."""

        def wsgi_app(environ, start_response):
            request = webob.Request(environ)
            return webob_app(request)(environ, start_response)

        return wsgi_app

And now::

    @wsgify
    def simple_app(request):
        """Simplest possible application object"""

        resp = Response()
        resp.status = '200 OK'
        resp.headers = [('Content-type','text/plain')]
        resp.body = 'Hello world!\n'

        return resp

WebOb conveniently provides that decorator function, and their form
does a little bit extra in the way of exception handling:
http://pythonpaste.org/webob/modules/dec.html

Finally, middleware typically accepts a single app as input and
returns a single app as output. A logical extension of this is a
composition that takes several apps as input and a single app as
output, so you could perversely write::

    def do_you_feel_lucky_punk(wsgi_app1, wsgi_app2):
        def wsgi(environ, start_response):
            if random() < 0.5:
                return wsgi_app1(environ, start_response)
            else:
                return wsgi_app2(environ, start_response)

        return wsgi

We will see a more rational use case when considering URL routing.

----

Let's take a step back for a moment. WSGI provides essentially two
mechanisms:

Transformation
    A method for taking input and producing output, called an app.

Composition
    A method for taking one or more apps and transforming it into
    another app.

These are powerful abstractions, and similar structures can be found
in stream processing applications. One example might be video editing
software:

Transformation 1
    Take a clip and apply color correction to it.

Transformation 2
    Take a clip and boost the sound.

Composition
    Take 1 and 2 (a set of transformations), and produce a new
    transformation that runs input through 1 and then 2.

Another might be the Unix command line:

Transformation
    ``cat words.txt | sort``

Composition
    ``nice sort``


.. [#] Additional tutorials and information can be found at `wsgi.org
   <http://wsgi.org/wsgi/Learn_WSGI>`_, though they are largely
   redundant in scope.


Structure of the URL and routing
--------------------------------

The backbone of a web request is its URL:
http://en.wikipedia.org/wiki/Url.

Consider the following URL::

    http://digg.com/news/technology/media/recent

The key piece of information here is the
``/news/technology/media/recent`` path, which indicates which page to
serve. Other components of interest are query variables::

    http://www.google.com/?q=S7+Labs

In this example, the URL contains a single query variable, "q", with
value "S7 Labs". URLs are not allowed to have spaces nor various other
characters, so arbitrary strings require encoding into a URL friendly
form. Python comes with libraries for doing this:
http://docs.python.org/library/urllib.html. Generally, the process of
transforming arbitrary text into a form that fits in a restricted
character set is called quoting, escaping, or encoding.

Path and query variables roughly map to functions and arguments. For
example, you might have a function::

    def get_recent_tech_news(num=10):
       """Return the last NUM news items, 10 by default."""

       ...

In URL land, we might have::

    /news/technology/recent (returns 10 by default)
    /news/technology/recent?num=20

The URL path is analogous to a function, and query variables are
analogous to function arguments. This rule generally produces
reasonable mappings, though there are some notable exceptions:

  - If you require the URL to be user (or search engine) friendly,
    then you may want to insert parameters into the path. For example,
    ``/user?username=john``, though it may correspond to a function
    ``get_user(username='john')``, is likely too complicated for
    general users who may want to be able to get directly to John's
    page by directly typing in the URL. ``/user/john`` is much
    cleaner. It's also ambiguous whether or not search engines fully
    weight query parameters when indexing pages. Crawlers must pay
    attention to them at some level; the question is if the ``john``
    keyword gets more weight for the page with ``/user/john`` or
    ``?username=john``.

  - In some cases, you may want to infer the direct object of an
    action from user hidden information, such as logged in state. For
    instance, a ``/dashboard`` route may always display an editing
    interface for the currently logged in user, and thus need not be
    specified in the URL. These kinds of paths are generally private,
    in the sense that you must be logged in, and search engines are
    not allowed to have access.

URLs should be considered permanent. Moving them wrecks havoc on
search engines and bookmarked links. A related problem is inserting
mechnical details into the URL, such as ``cgi-bin`` in paths, or
appending ``.html`` to the URL. Should any particular detail change,
the URL would either have to move, or become a lie. Tim Berners-Lee
has a classic essay on the topic, `Cool URIs Don't Change
<http://www.w3.org/Provider/Style/URI.html>`_, which links to Jakob
Nielsen's `own take <http://www.useit.com/alertbox/990321.html>`_.

The mechanism for getting from a request with path ``/foo/bar?q=qux``
to the web app ``foo_bar`` is called routing or dispatching. You will
now build a simple routing mechanism using Python regexes:
http://docs.python.org/library/re.html.

When designing a system, you should try to anticipate the input
size. As a reference, the Songza application currently contains around
120 routes. A large site might have roughly a few hundred routes, or
even a few thousand at most, but would be unlikely to have millions of
routes. The relatively small number implies that linearly searching a
list of routes is likely a reasonable strategy.

For Flipper, we would like to define routes like so::

    def login_app(request):
        ...

    def logout_app(request):
        ...

    def user_app(request, username):
        ...

    def about_app(request):
        ...

    def index_app(request):
        ...


    routes = [('/login', login_app),
              ('/logout', logout_app),
              ('/user/(?P<username>\w+)', user_app),
              ('/about', about_app),
              ('/', index_app)]

    # main wsgi app
    flipper_app = RouterApp(routes)

The algorithm is roughly::

    def route_algorithm(request, routes):
        for r, app in routes:
            if request.path matches r:
                args = extract from request.path and r
                return app(request, args)

        raise Page Not Found

Notes:

1. Matching should be done in the order in which it's defined, ie if a
   path matches two different route rules, the first one should be the
   one that gets executed.

2. There is an implied ``^`` and ``$`` at the beginning and end of the
   route spec. Thus, the ``/foo`` spec matches the path ``/foo``, and
   not ``/foobar`` nor ``/barfoo``.

3. The input apps to ``RouterApp`` should take a request object and
   any matched portions of the regex. To simplify things, the app
   should return a rendered string, and use ``webob.exc.*`` to signal
   HTTP errors, such as "404 Not Found". For example::

       def user_app(request, username):
           user = flipper.get_user(username)
           if user:
               return "hello, " + username
           else:
               raise webob.exc.HTTPNotFound()

4. ``RouterApp`` should raise or pass through WebOb exceptions for
   standard HTTP errors. You should write middleware that catches 404
   exceptions and renders a user friendly error page (but be careful
   not to rewrite the HTTP error code!).

5. You do not have to write real ``*_app`` functions. You can merely
   use stub functions, like::

       def login_app(request):
           return 'login app!'

.. note:: Write ``RouterApp``.


Templating
----------

Web pages are almost entirely text, thus you'll find your apps will
generally be returning strings in the response body. Let's look at
``user_app`` again::

    @wsgify
    def user_app(request, username):
        resp = webob.Response()
        resp.body = 'hello, ' + username
        return resp

The return here is actually malformed, since it is not valid HTML. A
full HTML page for the user ``wes`` might look like this:

.. code-block:: html

    <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
                          "http://www.w3.org/TR/html4/loose.dtd">
    <html>
      <head>
        <title>wes</title>
      </head>

      <body>
        <h1>wes</h1>

        <p>Hello, wes!</p>
      </body>
    </html>

Producing lengthy HTML output from within Python is problematic
because:

1. Python's syntax makes it awkward to produce long strings.

2. Python has rudimentary variable substitution facilities for
   inserting data into strings.

3. In a large scale web app, non-programmers (designers) often times
   write the HTML, and so requiring them to touch Python code is an
   iffy proposition.

To fix these problems, web frameworks use template languages. With a
template language, a designer writes HTML, but uses special template
variables to insert data into the page. For example:

.. code-block:: html

    <html>
      <head>
        <title>{{ user.username }}</title>
      </head>

      <body>
        <h1>{{ user.username }}</h1>

        <p>Hello, {{ user.username }}!</p>
      </body>
    </html>

The framework is usually structured so that the designer can simply
drop in HTML files, and interface to the rest of the web app flows
through the template variables. The designer then views the template
variables as an API, and the developer views them as the end WSGI
app. For instance, the designer writes the above HTML into
``user.html``, and the developer writes the following::

    def user_app(request, username):
        user = flipper.get_user(username)
        if user:
            return flipper.render('user.html', { 'user': user })
        else:
            raise webob.exc.HTTPNotFound()

For Flipper, we will be using `Jinja2 templates
<http://jinja.pocoo.org/>`_. The documentation is extensive. You
should first read it from the `designer's point of view
<http://jinja.pocoo.org/docs/templates/>`_, and then familiarize
yourself with `how the programmatic side works
<http://jinja.pocoo.org/docs/api/>`_.

Consider the render function described in ``user_app``. It should take
two arguments, a template filename, and a context dictionary, and:

1. Create a Jinja2 template object for the given filename. You should
   pick a reasonable location for all of the templates in the
   framework. Generally this is a 'templates' directory within the
   project.

2. Return the rendered template using the given context dictionary as
   arguments. The return type should be a string.

3. Pay careful attention to error conditions. If there are rendering
   errors, or the template file is not found, you want to return a 50x
   server error.

.. note:: Write ``flipper.render``.


HTML
----

`HTML <http://en.wikipedia.org/wiki/HTML>`_ is a textual
representation of data that can be rendered by a browser into a visual
form for a user. It consists of a series of tags, which are usually
found in open and close pairs. An open tag is text separated by ``<``
and ``>``, and the matching closing tag is the same, except that the
text is prepended by a ``/``. For example, an HTML document consists
of header and body sections, enclosed in ``head`` and ``body`` tags,
which are themselves inclosed in ``html`` tags:

.. code-block:: html

    <html>

      <head>
      </head>

      <body>
      </body>

    </html>

HTML *markup* languages in general provide a structure to describe
content while considering presentation a separated concern. A document
may specify the relative importance of content elements, but not
dictate exactly how that importance should be visually rendered:

.. code-block:: html

    <!-- comment tags -->

    <h1>Elements of Web Architecture</h1> <!-- heading 1, the most important heading -->

    <h2>Flipper, a Federated Twitter Clone</h2>

    <p> <!-- paragraph tag -->
      Over the next few lessons, we'll construct a custom web
      framework and Twitter clone called Flipper.
    </p>

    <h3>WSGI</h3>

    <p>
      The Web Service Gateway Interface (WSGI, pronounced wiz-ghee)
      is an interface specification first defined by

      <!-- anchor tag: specifies a hypertext link (note that
	   whitespace is unimportant) -->
      <a href="http://www.python.org/dev/peps/pep-0333/">PEP 333</a>.
    </p>

Some elements, such as ``img``, do not require a closing tag. In this case, the tag itself ends in ``/>``::

    <img src="/hello.jpg" />

.. note:: `w3schools <http://www.w3schools.com/html/>`_ appears to
   have won the Google site listing wars for HTML tutorials and
   references. You should read the introduction and get familiar with
   the basic HTML tags.

There is a notion of "semantic" markup, which is at times
misunderstood. Semantic markup generally means that information you
present in an HTML file uses tags in appropriate ways. For example,
you may use ``h1`` tags for the titles of chapters, or ``ul`` tags for
lists of items. There is nothing that prevents you from constructing a
list using a series of ``p`` elements, however doing so might put you
at the wrath of the search engine optimization gods. Search engines
presumably understand relative tag importance (``h1`` tags are more
important than ``h2`` tags, tags deep in a nested hierarchy are less
important than inclosing tags, etc).

Some uses of the term "semantic" imply a complete decoupling of
content and presentation. Old style HTML allowed for indicating text
as being bold by using ``b`` tags. New "semantic" HTML says that you
should indicate text as *important* by using ``em`` (emphasis) tags,
but defer the decision on *how to indicate importance* to some other
mechanism (CSS, or Cascading Style Sheets, in this case).

It is not possible for content and presentation to be completely
separated. Two paragraphs, for example, may only make sense if one is
presented before the other, and so there is always at least a linear
presentation ordering on content that can be implied from the way the
markup is written.

Once you realize that the division between content an presentation is
fungible, you open yourself to the possibility of building
presentational tricks and tools into markup. `Blueprint CSS
<http://www.blueprintcss.org>`_ and `960 Grid <http://960.gs>`_ are two
examples of very popular presentation frameworks that do exactly that.

The content / presentation relationship is further muddied by the
insight that one layer's content might be another layer's
presentation. Take, for example, the notion of a user with information
stored inside of a database. An administrator may want to view the
user's information via a web page or via a text interface produced by
an internal tool. The content, in this example, is the database record
for the user, and the presentation is the HTML or text output. When
considering a content / presentation abstraction, you also need to
consider what layer of the system you're talking about.


SQL
---

Structured Query Language (SQL, pronounced ess-queue-el, or sometimes
sequel), is a language for pulling information out of a relational
database.

You can think of relational databases as a series of tables with fixed
columns, and SQL is the way that one table ties in with another.

For example, the Flipper database might have a user table:

========  ========  =================
username  password  registration_date
========  ========  =================
wes       wes123    2011-06-06
roy       roy222    2011-06-08
chris     chris192  2011-06-10
joe       joejoe    2011-07-04
========  ========  =================

And a table of flips:

===  ========  ===================  ====
id   username  time                 flip
===  ========  ===================  ====
1    wes       2011-06-06 12:32:25  hello world!
2    wes       2011-06-06 12:35:21  could be fun
3    roy       2011-06-08 09:12:47  ahoy, matey
4    chris     2011-06-10 23:32:11  @wes I agree
5    chris     2011-06-10 23:33:42  #sasquatch I see him!
===  ========  ===================  ====

Using SQL, you can retrieve information from tables::

    > select * from users;
    wes|wes123|2011-06-06
    roy|roy222|2011-06-08
    chris|chris192|2011-06-10
    joe|joejoe|2011-07-04

And you can tie data together using the ``join`` operator::

    ; all flips for user wes
    > select flip from flips where username = 'wes';
    hello world!
    could be fun

    ; all flips for users who signed up before 2011-06-09
    > select flip from flips join users on
             flips.username = users.username where users.registration_date < '2011-06-09';
    hello world!
    could be fun
    ahoy, matey

Flipper will use `SQLite 3 <http://www.sqlite.org/>`_, which is small
SQL implementation that requires minimal administrative work. It is
ideal for development, as the data resides in a file that can be
copied and easily removed. In contrast, an SQL server such as MySQL
typically requires root access, and has much more in the way of
authentication, remote connectivity, replication, tools, and other
useful features. [#]_

.. note:: You should run through the tutorial exercise at `SQLzoo
   <http://sqlzoo.net/3.htm>`_, and familiarize yourself with `SQLite
   <http://www.sqlite.org/docs.html>`_. You should also look at
   Python's `sqlite3 module
   <http://docs.python.org/library/sqlite3.html>`_ and note the
   questionmark param style.

If you have used a web framework, you might be familiar with Object
Relational Mappers. An ORM is a library that translates SQL queries to
and from a language's object model. It vastly simplifies development,
and generally cuts down on the need to understand SQL. We're purposely
using SQLite directly for Flipper so that you might better understand
the nuts and bolts.

.. [#] http://www.sqlite.org/whentouse.html


The Flipper Model
-----------------

Now comes the fun part! We'll build an internal API for managing users
and flips. First, we'll need to initialize the database with
tables. We'll start with a basic structure:

.. literalinclude:: flipper_model.py

We are storing times as seconds since the epoch, ie `Unix time
<http://en.wikipedia.org/wiki/Unix_time>`_. The main advantage to
doing this is that it eliminates timezone ambiguities; the timezone of
the server, the value stored in the database, and the value assumed by
the application must all match up for correctness. The disadvantage is
that you'll then have to convert from an integer into a language's
native time object wherever you need more specific time information.

.. note:: Study the structure of ``FlipperModel``, and make sure you
   understand ``_fetchone`` and ``_fetchall``. Add a ``flips`` table
   to ``init_tables`` and write the following functions:

   - ``get_users() => list of users``
   - ``create_flip(username, flip) => True or False``
   - ``get_flips(username) => list of flips, sorted newest to oldest``


API + Routes = Web Site
-----------------------

Flipper's structure should becoming clear. Recall these routes::

    routes = [('/login', login_app),
              ('/logout', logout_app),
              ('/user/(?P<username>\w+)', user_app),
              ('/about', about_app),
              ('/', index_app)]

We can now build a real ``user_app``::

    def user_app(request, username):
        user = flipper.get_user(username)
        flips = flipper.get_flips(username)
        if user and flips:
            return flipper.render('user.html',
                                  { 'user': user,
                                    'flips': flips })
        else:
            raise webob.exc.HTTPNotFound()

.. note:: Construct an ``about_app`` that renders a static page
   describing the Flipper, and a ``user_app`` that renders a list of
   flips. You can directly call your ``create_flip`` function from a
   script to insert data into the system for the time being for
   testing purposes.


Representational State Transfer
-------------------------------

REST is a method of organizing resources and actions that follows a
few well laid out guidelines. It's become a bit of a buzzword in
recent years, and is often times mentioned with web based APIs, though
the ideas aren't necessarily restricted to just APIs. The `Wikipedia
article
<http://en.wikipedia.org/wiki/Representational_State_Transfer>`_ about
REST is good.

The REST guidelines are not tied to any specific protocol, though the
most well known implementation is the HTTP standard. As a result, if
you hear talk about a REST interface, it's usually implied that it's
built on top of HTTP requests.

An HTTP request is a (usually) short lived TCP connection and exchange
of information between a client (browser) and web server (Apache,
Nginx, or Flipper in our clase). The client supplies key-value pairs
of information known as the headers, as well a set of variable name to
value mappings to the server. As we've previously seen, if the name /
value mappings are sent embedded in the URL, they are called query
parameters. If they are sent in the body of the request, and thus
hidden from view except through an inspection of data on the wire,
they are called POST variables.

Each HTTP request is accompanied by a method type, which roughly
defines the intent of the request. One advantage for doing so is that
the HTTP aware layers between the client and server can use the method
type to decide on various kinds of optimizations. If the HTTP response
does not specify otherwise, intermediate layers may choose to cache
data. PUT and DELETE requests are idempotent, and so a client knows it
may resend them without harm. You've most likely seen a browser
display an alert when reloading a page, warning that it may have to
resend data to the server. These are most likely POST requests, which
are not guaranteed to be idempotent.

The vast majority of page requests are GETs, and a significant
fraction are POSTs and PUTs, which are often times mistakenly
interchanged. DELETEs are rare, though strict-to-the-letter REST
requires they be used. Some older browsers do not support PUT or
DELETE for *page requests*, however all browsers support all method
types if called from Javascript. As REST APIs are generally meant to
be used by programs, method support is essentially a non-issue.

We will be coming back to REST when we look at AJAX and how to build
highly interactive pages.


The Form Loop
-------------

HTML forms are interface elements that allow a user to type in data
into fields on a web page and send it to the server. The server
receives the data and validates the input, ie ensures that the values
make sense and can be safely used to manipulate the internal
state.

An HTML form element looks like:

.. code-block:: html

    <form action="/edit" method="post">
      username: <input type="text" name="username" />
      password: <input type="text" name="password" />

      <input type="submit" value="submit" />
    </form>

This form element defines two input fields and a submit button. On
submission, the browser performs a ``POST`` request to the ``/edit``
path with variables ``userame`` and ``password`` filled in with the
input the user's input.

On the server side, we receive a request like::

    def signup_view(req):
        if req.method == 'POST':
            username = req.str_params['username']
            password = req.str_params['password']

            return "signup received for %s with password %s" % (username, password)
        else:
            raise webob.exc.HTTPNotFound()

The typical form submission loop, then, looks like:

1. Render form html for user, browser waits for user input.

2. User clicks submit.

3. Browser sends data to server.

4. Server processes data. On success, renders success page. On
   failure, renders failure page (or input page with failure
   indications).



Validation
----------

Step #4 from the form loop generally contains two parts: validation of
input data, and subsequent manipulation of model. This usually fits a
pattern like:

.. code-block:: python

    data = receive data from client
    form = schema of valid data
    if form(data).is_valid():
        process(data)
        if processing succeded:
            return success page

    return error page to user with helpful message

We will be using `FormEncode <http://formencode.org>`_, which is a
library that provides handy validation and a framework for
constructing compound validators (checks between two fields in a form,
such as "password" and "re-enter password").

.. note:: Note that FormEncode has a decent high level description of
   what it does and how it works, however detailed information about
   validators are located in docstrings. You can view those by
   starting up a Python interpreter and running the ``help`` command::

       >>> import formencode.validators
       >>> help(formencode.validators.String)

We generally want the error page to be the same as the input page, so
that a user can fix input and resubmit. A straightforward way to
achieve this is by submitting an error context variable into the form
submission page template. Take, for example, this basic page:

.. code-block:: html

    <html>

      <!-- header here... -->

      <body>

        <!-- This html page is at the /edit path. Note the following
             form posts to /edit as well. -->

        <form name="input" action="/edit" method="post">
          username: <input type="text" name="username" />
          password: <input type="text" name="password" />

          <input type="submit" value="submit" />
        </form>
      </body>

    </html>

We can modify it like so:

.. code-block:: html

        <form name="input" action="/edit" method="post">
          {% if errors.username %}
          <span>{{ errors.username }}</span>
          {% endif %}
          username: <input type="text" name="username" />

          {% if errors.password %}
          <span>{{ errors.password }}</span>
          {% endif %}
          password: <input type="text" name="password" />

          <input type="submit" value="submit" />
        </form>

And now when we render the template, we pass in appropriate context
info::

    errors = {}
    if req.method == 'POST':
        # try to validate and modify data
        try:
            schema = SignupSchema()
            cleaned_data = schema.to_python(request.str_params)
            # if we get here, this means that validation succeeded
            do_something_with_data(cleaned_data)
            return flipper.render('signup_complete.html')
        except formencode.Invalid, e:
            errors = e.unpack_errors()

    return flipper.render('signup.html',
                          { 'errors': errors })

On the first ``GET`` request, the ``errors`` dict will be empty, and
so the rendering of ``signup.html`` will not produce any of the error
message spans. If the user submits the form, the ``POST`` request will
come through and get caught in the validation ``try / except``
block. If there is a validation error, ``errors`` gets populated, and
subsequently rendered. If validation succeeds, we render the
``signup_complete.html`` template.

We are now ready to create a ``/flip`` route. Here is the route structure with ``/flip``::

    routes = [('/login', login_app),
              ('/logout', logout_app),
              ('/flip', flip_app),
              ('/user/(?P<username>\w+)', user_app),
              ('/about', about_app),
              ('/', index_app)]

.. note:: Construct ``flip_app``, which should be a page where the
   user can type in a username and flip text, both of which should be
   validated as being non-empty, submit the data, and have it recorded
   via the ``create_flip`` model function. The flip schema should
   additionally allow only flips of 140 characters (use the ``max``
   argument to the ``String`` validator).


Cookies
-------

`Cookies <http://en.wikipedia.org/wiki/HTTP_cookie>`_ are pieces of
information that are stored in a user's browsing session, transmitted
to the server on each page request, and able to be manipulated by the
server in the page response. Without cookies, browsers are stateless
across page requests, and so interactions involving multiple pages
would be difficult, but not impossible. (How else might you transfer
state across page requests?)

There are two notable problems with cookies:

1. Cookie data can be sniffed off the wire through unencrypted http
   requests. Thus, they should not hold sensitive information.

2. Cookie data is included in both requests to the server and
   responses from the server. If the amount of data is large, this can
   affect performance.

To solve these problems, web frameworks provide session handling,
which is a mechanism for storing data on the server that is linked up
with a unique id stored in a client cookie.

On a user's first visit to a site, the server creates a unique id that
it places inside of a cookie, which is then recorded by the user's
browser. On the next page request, the browser sends that unique id to
the server, which can match it against data it is storing in the
database on behalf of the user.

A common use for sessions is to hold authentication information. You
might have a login app like so::

    def login_app(req):
        if req.method == 'POST':
            username = req.str_params['username']
            password = req.str_params['password']
            if is_auth(username, password):
                session = get_session(req)
                session['username'] = username
                return flipper.render('login_successful.html')
            else:
                return flipper.render('login_failed.html')

And a logout app::

    def logout_app(req):
        session = get_session(req)
        del session['username']

We will be using Paste's `session handling middleware
<http://pythonpaste.org/modules/session.html>`_, which is sufficient
for Flipper, though not production quality. A production quality
session handling middleware would have at a minimum database
support. There are many options in the WSGI world.

.. note:: Write a proper ``login_app`` and ``logout_app`` that uses
   form validation for checking input (don't forget to specify a
   maximum size for username and password fields!), and for checking
   the user's password against the database.

   Write ``signup_app``, which should, obviously, provide an interface
   for the user to sign up for your site. It should at a minimum
   perform these validations:

   1. Usernames should be alphanumeric and be no more than 10
      characters long. Usernames should also not already be used in
      the system.

   2. Passwords should be no more than 20 characters long.

   3. The account creation form should ask for the password twice and
      verify that both inputs match.

   Add any other validations that you think might be necessary.

   Storing passwords in the database might pose a security risk if
   your site were to be hacked, or a disgruntled, unethical, or
   coerced employee were to peek at the database. A common technique
   for handling these situations is to store the password using a one
   way hash, such as MD5 or SHA. Because there is no (known) way to
   recover the original password from the database, you reduce the
   potential for leaking sensitive information. Implement this for
   your authentication scheme using Python's ``hashlib`` module.


Following
---------

We will now construct a simple "follow" feature, which will allow
users to keep track of other user's flips.

First, build the ``follow`` table:

===  ========  =========
id   username  following
===  ========  =========
1    wes       chris
2    wes       roy
3    chris     wes
===  ========  =========

In this example, Wes is following Chris and Roy, and Chris is
following Wes. Roy marches to the beat of his own drummer.

This schema should lend itself naturally to an SQL query to produce
the most recent flips for the set of all followed users. You could
also perform a multistep query: one to lookup the followed users, and
then a query for each of them, plus an aggregation step to combine the
results into a single sequence. This latter method is more
inefficient, because of the multiple disk accesses, however it may be
easier to understand.

.. note:: Build the follow table, and write ``add_follow`` and
   ``get_followed_flips`` into the API.

   Next, place an input field on the user's page that appears only if
   the user is logged in, and allows the user to enter the username of
   someone he wants to follow.


Denormalization
---------------

If user Jack flips "ahoy, @Jill", Jill may want to be notified of this
direct mention. The data is all in the ``flip`` column of the ``flip``
table, however a linear search of all the entries for "@Jill" would
become increasingly inefficient as the site accumulates flips.

To solve this, we can build what is known as a reverse index. Each
time that we write a flip to the database, we can check the text for a
mention and insert an entry into another table that is keyed on
username. For example, consider the flip:

===  ========  ===================  ====
id   username  time                 flip
===  ========  ===================  ====
4    chris     2011-06-10 23:32:11  @wes I agree
===  ========  ===================  ====

We can extract "@wes" (most conveniently done with regexes) from the
flip and insert that into a ``mention`` table:

========  =======  ===================
username  flip_id  time               
========  =======  ===================
wes       4        2011-06-10 23:32:11
========  =======  ===================

A search for wes's most recent mentions is now a straightforward
efficient query. The inclusion of the timestamp allows us to easily
limit the number of "most recent" flips we show the user.

The reverse index is an example of what is called data
denormalization. Normalization (without the *de*) is a generally good
practice in which you design your data model so that every piece of
information is stored in a single location. This reduces the
possibility of bugs creeping into the system in different places and
causing data to diverge.

Suppose we were to build an interface that allowed a user to edit a
flip. If the user were to remove a mention, then we would have to be
careful to also remove the corresponding entry in the ``mention``
table. Because information about whether or not flip #4 contains a
mention to Wes is contained in two different locations, our code must
be careful to stay consistent. In a much larger, complex system, the
engineer responsible for the "edit flip" feature may not be the same
engineer who built the mention system, and the two may not even be
employed at the company at the same time! Poor programming practices
or communication may lead to the introduction of some subtle bugs.

There is a principle called `Don't Repeat Yourself
<http://en.wikipedia.org/wiki/Don't_repeat_yourself>`_ (DRY), which
stresses that there should be a single authoritative location for any
piece of data or code.

But as you have seen in this simple situation, denormalization is
difficult to avoid. In this case, we could have kept the data
normalized if we relied on SQLite's full text search capabilities,
however that would not have made for an interesting exercise. Using
the built-in FTS also means that we would have no control over
stemming or input transformations (like spell checking) that would
allow us to produce more robust search solutions for the user. FTS is
also not a part of standard SQL, so it would have tied us down to
SQLite, or required re-implementation if we moved to another SQL
server.

We could have taken our denormalization one step further. Notice that
producing a list of mentions for a user requires at least two queries
to the database: one to get the flip IDs, and one to get the content
of the flips. We could eliminate the second query simply by storing
the content of the flip directly in the ``mention`` table.

Denormalization is a tool that can be incredibly useful if judiciously
used.


.. note:: Create a ``mention`` table, an API for adding entries and
   retrieving flip IDs from the ``mention`` table, and modify the
   ``create_flip`` function to build the reverse index. Note that
   there could be multiple mentions within a single flip.

   Add into the user page view a list of the 5 most recent mentions.

   Construct a similar system for `hashtags
   <http://en.wikipedia.org/wiki/Hashtag#Hashtags>`_, which are user
   generated subject identifiers that begin with a "#".

   Construct an ``index_app`` which has an input field that takes a
   series of hashtags and displays the most recent flips with that
   hashtag.


Caching
-------

Here are some numbers that every engineer should know (as of 2010),
excerpted from `here
<http://www.quora.com/What-are-the-numbers-that-every-computer-engineer-should-know-according-to-Jeff-Dean>`_:

* Main memory reference: 100 ns [#]_
* Send 2K bytes over 1 Gbps network: 20,000 ns
* Read 1 MB sequentially from memory: 250,000 ns
* Round trip within same datacenter: 500,000 ns
* Disk seek: 10,000,000 ns
* Read 1 MB sequentially from network: 10,000,000 ns
* Read 1 MB sequentially from disk: 30,000,000 ns

Note the orders of magnitude difference between access times for RAM
and disk. This suggests that if we can avoid touching disk, we should.

For Flipper, we will build a simple in-memory caching system modeled
after one you might find in production frameworks. Our caching system
will have a few essential functions:

1. Store Python objects in memory.

2. Associate expiration times with objects.

3. Clear out expired items.

4. If full, remove items according to a least recently used algorithm.

The API should have a flavor like so::

    cache = flipper.get_cache()
    key = "foo"
    expiry = 3600 # one hour from now

    if key in cache:
        return cache.get(key)
    else:
        value = compute_value()
        cache.set(key, value, expiry)
        return value

    cache.expire(key) # manually invalidate the key

.. note:: Build the cache API. I will leave the implementation up to
   you.

   Once the cache API is stable and tested, use it to cache flip
   lookups in ``user_app`` and search results. Be sure to invalidate
   the appropriate cache entries when new data enters the system.

.. [#] Additional numbers:

   1. L1 cache reference: 0.5 ns
   2. L2 cache reference: 7 ns
   3. Main memory reference: 100 ns

   What you learn in school is that algorithmic order of growth
   overshadows constant factors. In most cases you should prefer the
   algorithm that has a slower growth function. However, consider that
   the difference between L1 access time and main memory is a factor
   of 200! For a small enough input size, it may actually be faster to
   use a less efficient algorithm if it means that all of the data can
   fit within the processor cache.

   The same principle applies to disk and memory access. It is
   sometimes faster to use a less efficient algorithm that sits entire
   in RAM than a more efficient one that has to touch disk.

   Missing from this list of numbers is Solid State Drive, which has
   an access time around 100,000 ns.


Federation
----------

Constant outage was a problem with Twitter in the early days, so much
so that their "fail whale" server error page `became an iconic image
<http://www.readwriteweb.com/archives/the_story_of_the_fail_whale.php>`_. One
route Twitter could have gone to scale out would have been to build a
federated protocol, ie one in which any number of site administrators
could run identical copies of the Twitter service, which would
communicate with each other in a similar way as Mail Transfer Agents
(email), and Jabber (Google Chat).

In a federated system, one or more components of it can fail without
affecting the overall system. Distribution of components has
advantages, but also can suffer from complexity and consistency
issues. The CAP theorem states that in a distributed system, you can
have only two of thee properties: consistent data, system
availability, and tolerance to network (communication) partitions. We
will choose a simple protocol that will allow for `eventual
consistency
<http://www.allthingsdistributed.com/2008/12/eventually_consistent.html>`_,
ie different portions of our system may have a different view of the
data in the entire system, but will be tolerant to network and system
outages and will converge on the "correct" view eventually.

Suppose that we have two Flipper servers running at ``local.com`` and
``foreign.com``, and Jack at ``local`` wants to follow user Jill at
``foreign``. Jack should be able to go to his own page and enter in
``jill@foreign.com``, which will make an entry in his ``follow``
table.

The original ``follow`` table assumes that all users reside on the
same system, and so needs a bit of tweaking to support foreign Flipper
servers. One way to do this is to build a new column containing the
server name if the follow entry is to a foreign user, but blank if it
is for a local user.

Once that is in place, the code for looking up flips will need to be
modified to retrieve data from the remote Flipper server. The local
Flipper can do this with a technique known as screen scraping: it can
make an HTTP request to the foreign user's page, parse the resulting
HTML, and display that to the local user. This can problematic. In
particular, programmatic HTTP libraries seldom have Javascript
support, and many sites insert data into the DOM tree after page load,
using a technique known as Ajax. We will not go into it now, but
suffice it to say, screen scraping is becoming harder to do as sites
become more dynamic.

Instead, we will build a protocol using a data interchange format
called `JSON <http://www.json.org/>`_. JSON is a syntax for expressing
arrays and dictionaries of common data types (strings, integers, and
floating points) which is identical to Javascript syntax. The
convenience here is that Javascript, which is most commonly used for
client side interactions on a site, can load a JSON encoded object
from an HTTP request and simply use the ``eval`` function to turn it
into a native object. JSON libraries are simple enough to implement
that all major languages have done so, and thus it makes for a
reasonable, simple method for interchanging data between programming
languages and platforms. [#]_

.. note:: This exercise consists of several components:

   1. Appropriately modify the ``follow`` table to accept foreign
      users.

   2. Modify follow box if necessary to accept input for foreign
      users.

   3. Expose a user's flips as a JSONized array using Python's
      ``simplejson`` module. This should be done in the ``user_app``
      path if a special query variable called ``format`` is set to
      ``json``.

   4. Write a library that takes a foreign username and a hostname and
      uses the Python ``urllib`` library to retrieve that user's flips
      in JSON format. Note that to achieve system availability
      (stability), your program can not crash and burn should
      something go wrong with the request to the foreign server. Thus,
      it must handle several cases: HTTP and network protocol errors,
      data errors, and timeouts (a slow remote server should not sieze
      up the page for the local user).

   5. Tie it all together: when displaying followed flips, you must
      now make remote calls to all foreign servers to retrieve flips
      for the local user.

If all goes well, your Flipper server should now be able to
communicate with other Flipper servers. Try it!

.. [#] Other popular data interchange formats include `XML
   <http://en.wikipedia.org/wiki/XML>`_, `protobuf
   <http://code.google.com/p/protobuf/>`_, and `MessagePack
   <http://msgpack.org/>`_.


Background Processing
---------------------

Notice that if a remote server is slow or unavailable, step #4 could
be quite inefficient, as rendering a user's page depends on making
multiple remote Flipper calls.

Some actions do not necessarily have to affect the system instantly,
and so it might be ok to offload computation into a separate process
if the user can tolerate some delay. In this case, we will retrieve
and cache flip data inside of the database in a background process
that runs outside of the web server.

We will make use of what is called a producer/consumer
queue. Typically, this design pattern requires the maintenance of a
separate queuing structure, where a producer inserts jobs, and a
consumer pulls jobs off and processes them. Our structure is a bit
different -- jobs will be permanent entries in a special
``follow_list`` table which contains a remote user, remote host, and
``last_updated`` column, which will contain a timestamp with a default
value of 0. Note that Jill's flips only need to be pulled down once to
satisfy all of the followers on ``local.com``, which is why we do not
simply store ``last_updated`` in the ``follow`` table.

You will need to build an external worker process that queries for new
follows (or follows that have not been updated since a certain
threshold, say 10 seconds), fetches updates from the remote server,
and then updates the timestamp with the current time.

Once you have a series of flips for the remote user, you'll need to
place these in a ``follow_cache`` table for quick access. We must
appease the data denormalization gods.

Subsequent calls to ``user_app`` for flips should not return duplicate
data, as this will become unwieldy to transmit as users generate
flips. Instead, ``user_app`` should accept a ``since`` parameter in
conjunction with ``format=json`` which will cause it to return only
flips that have IDs greater than ``since``. [#]_

Because you will be querying on the ``username`` and ``last_updated``
fields in the ``follow_list`` table, you will want to build indexes on
both of those columns. [#]_

Periodic worker functions are set up typically with either a time
based job system, like Unix's cron, or with an infintely looping
server. The advantage to a system like cron is that you can specify
your process to run at exact times. The disadvantage is that if your
processing function begins to take longer than the period at which the
job is configured to run, multiple instances of your worker process
will build up and potentially overwhelm the system resources.

We will use the infinite loop technique since we don't care that the
worker process is run *exactly* on schedule, but only *roughly* on
schedule. It's important to sleep for a short period of time (usually
from a fraction of a second to minutes, depending on the application's
needs) in order to prevent the worker process from spinning and
consuming all of the system resources. In this case, since we are
checking for new flips every 10 seconds, a delay of 1 second is
reasonable.

.. note:: Make the appropriate modifications to ``user_app``, the API,
   and the database. Write ``flipper_pull.py``, the background worker
   process that pulls remote flips into the system.

.. [#] Why is ``since`` the flip ID rather than a timestamp?
   Unfortunately, you can not rely on timestamps from remote sources,
   as it's not guaranteed that the remote source actually has a
   correctly set clock. Servers usually run some form of NTP, which is
   a network time syncing protocol, however machines can still be
   subject to clock drift, especially if the hardware is bad and the
   drift is faster than the NTP protocol is allowed to adjust the
   clock. Another possibility is a malicious remote client attempting
   to do something subversive by passing in bad data.

.. [#] An index on a column that is not the primary key is called a
   "secondary index". Why don't we just build a secondary index on
   every column? Indexes require disk space (sometimes more than the
   data itself) and typically take log(n) time to insert a row, where
   n is the number of rows in the table. The space issue is especially
   troublesome if the table approaches the size of main
   memory. Remember that accessing disk is orders of magnitude slower
   than RAM, and so underutilized indexes increase the likelihood that
   an active index will get flushed out of the filesystem cache.


Javascript and AJAX
-------------------

HTML and CSS provide a fine foundation for basic interaction with a
site. If you want to do the fancy stuff (anything that moves or is
dynamically updated without changing the URL in the browser), you'll
have to use Javascript.

.. note:: Peruse `this Javascript tutorial
   <http://www.cs.brown.edu/courses/bridge/1998/res/javascript/javascript-tutorial.html>`_.

Few people write naked Javascript these days. Instead, they use
libraries and frameworks, which have varying levels of
complexity. Popular libraries are: `jQuery <http://jquery.com/>`_ and
`jQuery UI <http://jqueryui.com/>`_, `Prototype/Scriptalicious
<http://script.aculo.us/>`_, and `YUI
<http://developer.yahoo.com/yui/>`_. We will be using jQuery.

In addition to the Javascript library, a good debugging tool is
absolutely essential. `Firebug <http://getfirebug.com/>`_ can be
installed via Firefox, and Chrome ships with debugging tools built in.

When a page loads, the browser generates a DOM tree from the HTML
markup, which is what you see if you were to view the source of the
page. Because the DOM tree corresponds directly to the visual display,
you will have to manipulate it in order to dynamically update the
display. Debugging DOM manipulation almost always involve inspecting
the tree using a tool like Firebug.

Suppose we want to build into Flipper's index page an updating list of
most recent tweets. We can start off with a root for this list in the
HTML markup:

.. code-block:: html

    <ul id="flip-root">
        <!-- dynamically updated via ajax -->
    </ul>

Now we can insert items into this root with jQuery:

.. code-block:: javascript

    $("#flip-root").append("<li>dynamically inserted list item</li>");

``$`` is a valid identifier in Javascript. jQuery (and various other
frameworks) bind the global ``$`` name to their library, which is
essentially a function that can do various things depending on the
type of its argument.

In this case, ``$("#flip-root")`` is what is called a selector, which
examines the DOM tree for an element with an id of ``flip-root``, and
produces a jQuery DOM object which has useful functions defined in
it. The function we use here, ``append``, inserts a new DOM element
inside of the ``ul`` tags.

The jQuery API is very well `documented
<http://docs.jquery.com/Main_Page>`_. The sections on `manipulation
<http://api.jquery.com/category/manipulation/>`_ and `AJAX
<http://api.jquery.com/category/ajax/>`_ are essential
references. jQuery documentation is very extensive, and it has a very
large user base. Thus, there are many `tutorials
<http://docs.jquery.com/Tutorials>`_.

jQuery infers a lot from its arguments (in fact, this is par for the
course in Javscript coding culture). If the argument to ``append`` is
a string, jQuery will parse it as if it is HTML and create a new DOM
object. You can also pass in a jQuery object into append:

.. code-block:: javascript

    var li = $("<li>dynamically inserted list item</li>");
    $("#flip-root").append(li);

We can make an AJAX call to the index path like this:

.. code-block:: javascript

    $.get({ url: "/",
            data: { format: "json" },
            success: updateFlips,
            dataType: "json" });

Where ``updateFlips`` is a function:

.. code-block:: javascript

    function updateFlips(data) {
        // data is the decoded json object, so you can do something
        // with data['flip'], for example.
    }

The Javascript execution model is single threaded, and asynchronous
events are handled through one of two mechanisms: callbacks and
signals. We will be dealing only with callbacks.

All interaction on a page is halted while Javascript runs, so an
errant program can effectively lock up a browser window if written
poorly. Most browsers will detect this and give the user the option to
kill the window if this happens.

The ``$.get`` example attempts to retrieve the page at ``/``, which
could block (or not return at all). The browser puts this portion of
the call in the background (the "asynchronous" in the AJAX acronym),
and execution continues past the ``$.get``. When it completes, the
browser returns control back to the user and waits for input. If the
call to ``/`` completes before any user input, the browser fires off
the Javascript interpreter again and executes the ``updateFlips``
function.

To clarify, suppose that we have a call to ``/foo``, which blocks for
10 seconds.

.. code-block:: javascript

    $.get({ url: "/foo",
            data: { format: "json" },
            success: successCallback,
            dataType: "json" });

    alert('waiting for foo...');

The browser pops open an alert box [#]_ *immediately* after the
``get`` call, *not* after 10 seconds. After clearing the box, the user
can continue to use the page. 10 seconds later, ``successCallback``
will get called, assuming that no other Javascript is running at that
time. If other Javascript code is running, then ``successCallback`` is
queued up to run at some point the interpreter becomes free. Note that
if the user browses away from the page before ``/foo`` returns,
``successCallback`` will never get called. Exactly when
``successCallback`` will be called is undefined.

The callback strategy is a common pattern, however it can make for
some difficult to debug code. Javascript code should be very well
documented because of the labyrinthine nature of callbacks.

.. note:: You should add ``format`` and ``since`` parameters to
   ``index_app`` similar to ``user_app``. Define ``updateFlips`` so
   that it takes these flips, builds a ``li`` element, and appends it
   into ``flip-root``. It should do this on page load, and then on a
   10 second `timer <http://www.w3schools.com/js/js_timing.asp>`_.

.. [#] ``alert`` is your best friend. If you want to check if a piece
   of Javascript is getting called, the easiest thing is usually to
   throw in an ``alert`` statement. Firebug and Chrome, alternatively,
   have stepping tools.


Production Time
---------------

You have now completed all the essential activity of a Twitter clone,
a task that took a handful of professinal developers a weekend to
build. The big remaining problem is one of scale -- the Flipper system
as implemented can only be run on a single machine, most optimally
from within a single process. Your next task is to re-impelement
Flipper, this time with industrial strength development tools and
libraries. You should research and assemble the following components
as a start:

* `Django <http://www.djangoproject.com/>`_ for the web framework. It
  will include a routing system, templates, object relational mapper,
  and caching interface that you may find useful.

* `MySQL <http://www.mysql.com/>`_ will be the backend
  database. Django's ORM abstracts the database for development,
  however you will still need to become proficient at examining data
  within the MySQL server.

* `Memcached <http://memcached.org/>`_, a caching server.

* `Xapian <http://xapian.org/>`_, a full text search engine.

* `Blueprint <http://www.blueprintcss.org/>`_, a CSS framework for
  building pages on grid templates. Also examine `Compass
  <http://compass-style.org/>`_ if you are feeling ambitious.

* `Beanstalk <http://kr.github.com/beanstalkd/>`_, a produce/consumer
  queue.

* `jQuery <http://jquery.com>`_, a Javascript library. jQuery provides
  nicer methods to manipulate browser displays and handle client side
  interaction, as well as a framework for UI widgets.

The entire team should re-build Flipper as a coordinated effort. Good
luck!


Software Engineering Good Habits
================================

As you build Flipper, you should keep in mind some tools and software
engineering best practices.

* `Mercurial <http://mercurial.selenic.com/>`_. Source control becomes
  exponentially more important as your software gains complexity, and
  your team increases in size. It is a tool for allowing you to
  checkpoint your work, try out experiments without fear of losing
  stable work, and coordinate code changes with other
  developers. Everything other than trivial experiments that you plan
  to throw away should be version controlled.

  The two most popular distributed source control systems as of this
  writing are Mercurial and Git. Which one you use is ultimately a
  matter of preference (they are equally powerful and have equally
  large communities), and you will find zealots for both systems. I
  personally find Mercurial commands a little more intuitive and less
  prone to wiping out data. S7 uses Mercurial unless there is a good
  reason not to (a partner we work with already uses Git or CVS, for
  example).

  Joel Spolsky wrote a popular `Mercurial tutorial
  <http://hginit.com/>`_.

* `Unit Tests <http://en.wikipedia.org/wiki/Unit_testing>`_. As you
  design and build components of your system, you should make an
  effort to develop APIs so that they are unit testable. Unit tests
  serve not only as a sanity check on the design of an API, but also
  as a reference, and a way to know if a subsequent change broke
  behavior. Python's ``unittest`` and ``doctest`` modules are good
  places to start.

  An essential part of a good unit test suite is that each test is
  independent of every other test.  This lets you run any one test in
  isolation (which is really handy for debugging).  To make this work,
  every test has to start from a known state and perform whatever
  setup is required.  To make this easy, most test frameworks will
  create a brand new test object before running each test (Python's
  ``unittest`` does this).

  Before you can write a good test, you need to know what you're
  testing.  You need to be able to put an object or system into a
  known state, perform some action on it, and then verify that it is
  now in the desired new state.

  There are some tests that can not be done purely on the server
  side. `Selenium <http://seleniumhq.org/>`_ is a Firefox plugin that
  allows you to record interactions with a site and play them back for
  verification.

  Also see `criticism
  <http://rethrick.com/#unit-tests-false-idol>`_. The lesson is that
  tests need to be smart, not mechanical.

* `Bug tracking
  <http://www.joelonsoftware.com/articles/fog0000000029.html>`_, or
  defect lists. For a small project and a small number of
  collaborators, there is no need to use a full blown bug
  tracker. However, you should keep a spreadsheet or shared document
  at a minimum that lists all of the known defects. Ideally, `bugs
  should be fixed before writing new code
  <http://www.joelonsoftware.com/articles/fog0000000043.html>`_, but
  of course this is *hard* in the real world.

  `Bitbucket <http://bitbucket.org>`_ is a site that hosts Mercurial
  repositories with a bug tracker and wiki attached for free. It is an
  excellent resource if you are looking to collaborate on the cheap,
  or on the free. `GitHub <http://github.com>`_ is the equivalent in
  the Git world.

* `Agile development and continuous fill-in-the-blank
  <http://en.wikipedia.org/wiki/Agile_software_development>`_. Agile
  is a buzzword that's nearly crossed into the realm of
  meaninglessness. The core of the idea is that software defects (bugs
  *and* misfeatures) introduced early in development become
  increasingly expensive to fix as time passes. Thus, you need a
  development process that receives constant feedback *that can be
  used to modify future development cycles*. If the specifications are
  rigid and will never change, running through the Agile motions will
  not result in a more efficient operation.

  A principle of agile development is that you decrease the barriers
  to everything that you view as good. If user feedback on new
  features is good, then you decrease the barrier to pushing new
  features. In the web world, this is possible since everybody runs a
  single version of your software, controlled on your servers. In the
  iPhone world, you can not continuously deploy, and so the
  development process needs to reflect that.

  The root of agile development, found in the `Toyota Production
  System <http://en.wikipedia.org/wiki/Toyota_Production_System>`_, is
  fascinating. Toyota turned the assembly line methods developed by
  Ford on its head by integrating in constant feedback and quick
  recovery, and as a result transformed the car industry.



Design Pattern Emporium
=======================

Design patterns can be thought of as tactics to solve various coding
problems. They codify various ways to construct software so that it is
easier to maintain and share code.

There are many design pattern references, however I have collected
together the ones I believe are the most useful.

* `Observer <http://en.wikipedia.org/wiki/Observer_pattern>`_. Notice
  that when you added that mention and hashtag features, you had to
  modify the ``create_flip`` function. There may, in fact, be many
  similar features, all of which require some action to be taken when
  a user flips. You could structure this using an Observer pattern:
  when ``create_flip`` is called, it emits a signal which other
  components of the system can hook to. This decouples the components
  (``create_flip`` need not know what features depend on it), thereby
  making the interactions easier to extend and maintain.

* `MVP <http://en.wikipedia.org/wiki/Model_View_Presenter>`_ or `MVC
  <http://en.wikipedia.org/wiki/Model-view-controller>`_. Note MVP
  matches the structure of Flipper: view matches templates and apps,
  presenter matches the API, and model matches the data in the
  database. `Amix's take
  <http://amix.dk/blog/post/19615#Model-View-Controller-History-theory-and-usage>`_.

* `Producer / Consumer or Conversation
  <http://www.eaipatterns.com/ramblings/18_starbucks.html>`_. Handy
  when you want to separate out expensive computations from immediate
  feedback to the user. For example, a user does not immediately
  expect a flip to be searchable, or to reach another mentioned user
  the instant that it posts. The user might be ok with a delay of a
  few seconds to minutes, or even hours, so there is no need to insert
  the potentially expensive indexing operation into the flip
  save. Instead, we can queue the index operation for a later worker
  to consume.

* `Null Object <http://en.wikipedia.org/wiki/Null_Object_pattern>`_.
  The idea behind Null Object is to make interfaces more uniform.
  Let's say you have a function ``get_logged_in_user()`` which is
  supposed to return an object of class ``User``.  What do you do if
  there's no logged in user?  One solution is to return something like
  ``None`` (if you're working in Python). The problem there is that
  now you have something that's not a real object and you have to add
  all sorts of special tests to avoid trying to access its attributes
  and throwing an exception. Instead, you could return a Null Object
  -- one which has all the methods and attributes of ``User``, but
  does nothing (gracefully). This usually ends up simplifying code.


Reading
=======

Programming & Technology
------------------------

* `Code Kata <http://codekata.pragprog.com/>`_, Dave Thomas

* `REST Worst Practices
  <http://jacobian.org/writing/rest-worst-practices/>`_, Jacob
  Kaplan-Moss

* `Cleaner, more elegant, and harder to recognize
  <http://blogs.msdn.com/b/oldnewthing/archive/2005/01/14/352949.aspx>`_,
  Raymond Chen

* `The Joel Test: 12 Steps to Better Code
  <http://www.joelonsoftware.com/articles/fog0000000043.html>`_, Joel
  Spolsky

* `The Hundred Year Language
  <http://www.paulgraham.com/hundred.html>`_, Paul Graham

* `Foursquare Outage Post Mortem
  <http://groups.google.com/group/mongodb-user/browse_thread/thread/528a94f287e9d77e>`_


Productivity & Business
-----------------------

* `Maker's Scedule, Manager's Schedule
  <http://www.paulgraham.com/makersschedule.html>`_, `How To Start A
  Startup <http://www.paulgraham.com/start.html>`_, `How To Make
  Wealth <http://www.paulgraham.com/wealth.html>`_, Paul Graham

* `Real Artists Ship
  <http://www.folklore.org/StoryView.py?story=Real_Artists_Ship.txt>`_,
  Andy Hertzfeld

* `Strategy Letter V (aka, commoditize your complements)
  <http://www.joelonsoftware.com/articles/StrategyLetterV.html>`_,
  Joel Spolsky

* `Fail Quicker
  <http://www.fastcodesign.com/1663488/wanna-solve-impossible-problems-find-ways-to-fail-quicker>`_,
  Aza Raskin.
