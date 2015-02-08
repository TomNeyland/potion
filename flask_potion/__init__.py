from collections import OrderedDict
import inspect
import operator
from flask import current_app, make_response, json
from six import wraps
from werkzeug.wrappers import BaseResponse
from .exceptions import PotionException
from .routes import RouteSet
from .utils import unpack
from .resource import Resource, ModelResource

__version_info__ = (1, 0, 0)
__version__ = '.'.join(map(str, __version_info__))
__all__ = (
    'Api',
    'Resource',
    'ModelResource',
    'fields',
    'routes',
    'schema',
    'signals',
    'contrib'
)

class Api(object):
    """
    This is the Potion extension.

    You need to register :class:`Api` with a :class:`Flask` application either upon initializing :class:`Api` or later using :meth:`init_app()`.

    :param app: a :class:`Flask` instance
    :param list decorators: an optional list of decorator functions
    :param prefix: an optional API prefix. Must start with "/"
    """
    def __init__(self, app=None, decorators=None, prefix=None):
        self.app = None
        self.prefix = prefix or ''
        self.decorators = decorators or []
        self.endpoints = set()
        self.resources = {}
        self.views = []

        if app is not None:
            self.init_app(app)


    def init_app(self, app):
        """

        :param app: a :class:`Flask` instance
        """
        self.app = app
        app.potion = self

        self.max_per_page = app.config.get('POTION_MAX_PER_PAGE', 100)
        self.default_per_page = app.config.get('POTION_DEFAULT_PER_PAGE', 20)

        self._complete_view(''.join((self.prefix, '/schema')),
                            view_func=self.output(self._schema_view),
                            endpoint='schema',
                            methods=['GET'])

        for rule, view, endpoint, methods in self.views:
            self._complete_view(rule, view_func=view, endpoint=endpoint, methods=methods)

        @app.errorhandler(PotionException)
        def handle_invalid_usage(error):
            return error.make_response()

    def output(self, view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            resp = view(*args, **kwargs)
            if isinstance(resp, BaseResponse):
                return resp

            data, code, headers = unpack(resp)

            settings = {}
            if current_app.debug:
                settings.setdefault('indent', 4)
                settings.setdefault('sort_keys', True)

            data = json.dumps(data, **settings)
            resp = make_response(data, code)
            resp.headers.extend(headers or {})
            resp.headers['Content-Type'] = 'application/json'
            return resp

        return wrapper

    def _complete_view(self, rule, **kwargs):
        self.app.add_url_rule(rule, **kwargs)

    def _schema_view(self):
        definitions = OrderedDict([])
        properties = OrderedDict([])
        schema = OrderedDict([
            ("$schema", "http://json-schema.org/draft-04/hyper-schema#"),
            ("definitions", definitions),
            ("properties", properties)
        ])

        # TODO add title, description

        for name, resource in sorted(self.resources.items(), key=operator.itemgetter(0)):
            resource_schema_rule = resource.routes['schema'].rule_factory(resource)
            properties[name] = {"$ref": '{}#'.format(resource_schema_rule)}

        return schema, 200, {'Content-Type': 'application/schema+json'}

    def add_route(self, route, resource, endpoint=None):
        endpoint = endpoint or '.'.join((resource.meta.name, route.attribute))
        methods = route.methods()
        rule = route.rule_factory(resource)
        view = self.output(route.view_factory(endpoint, resource))

        for decorator in self.decorators:
            view = decorator(view)

        if self.app:
            self._complete_view(rule, view_func=view, endpoint=endpoint, methods=methods)
        else:
            self.views.append((rule, view, endpoint, methods))

    def add_resource(self, resource):
        """
        Add a :class:`Resource` class to the API and generate endpoints for all its routes.

        :param Resource resource: resource
        :return:
        """
        resource.api = self
        resource.route_prefix = ''.join((self.prefix, '/', resource.meta.name))

        # prevent resources from being added twice
        if resource in self.resources.values():
            return

        for route in resource.routes.values():
            self.add_route(route, resource)

        for name, rset in inspect.getmembers(resource, lambda m: isinstance(m, RouteSet)):
            if rset.attribute is None:
                rset.attribute = name

            for i, route in enumerate(rset.routes()):
                if route.attribute is None:
                    route.attribute = '{}_{}'.format(rset.attribute, i)
                resource.routes['{}_{}'.format(rset.attribute, route.attribute)] = route
                self.add_route(route, resource)

        self.resources[resource.meta.name] = resource
