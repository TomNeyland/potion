from .schema import Schema
from .utils import get_value
from .fields import Integer, Boolean, Number, String, Array, ToOne, ToMany, Date, DateTime, DateString, DateTimeString


class BaseFilter(Schema):
    """


    :class:`EqualFilter` is a special filter type. This is because an equality condition is can be written in the format
    ``{"property": condition}``, whereas every other filter needs to be written as
    ``{"property": {"$filter": condition}}``.

    Due to the way the equality comparison is done, users need to be watchful when comparing objects. Some
    object comparisons can be ambiguous, e.g. `{"foo": {"$foo": "bar"}}`. If a condition contains an object with
    exactly one property, the name of the property will be matched against all valid filters for that field. If
    necessary, the equality filter can be declared explicitly to avoid comparing against the wrong filter,
    e.g. `{"foo": {"$eq": {"$foo": "bar"}}}`.

    Multiple filters can have the same filter name so long as they are not valid for the same field types. For example,
    :class:`StringContainsFilter` for strings and :class:`ContainsFilter` for arrays.
    """

    def __init__(self, name, field=None, attribute=None):
        self.attribute = attribute or field.attribute
        self.field = field
        self.name = name

    def op(self, a, b):
        raise NotImplemented()

    def _schema(self):
        raise NotImplemented()

    def _convert(self, value):
        return self.field.convert(value)

    def convert(self, instance):
        if self.name is None:
            return Condition(self.attribute, self, self._convert(instance))
        else:
            return Condition(self.attribute, self, self._convert(instance["${}".format(self.name)]))

    def schema(self):
        if self.name is None:
            return self._schema()
        return {
            "type": "object",
            "properties": {
                "${}".format(self.name): self._schema()
            },
            "required": ["${}".format(self.name)],
            "additionalProperties": False
        }


class EqualFilter(BaseFilter):
    def _schema(self):
        return self.field.response

    def op(self, a, b):
        return a == b


class NotEqualFilter(BaseFilter):
    def _schema(self):
        return self.field.response

    def op(self, a, b):
        return a != b


class NumberBaseFilter(BaseFilter):
    def _schema(self):
        if isinstance(self.field, (Date, DateTime, DateString, DateTimeString)):
            return self.field.response
        return {"type": "number"}


class LessThanFilter(NumberBaseFilter):
    def op(self, a, b):
        return a < b


class GreaterThanFilter(NumberBaseFilter):
    def op(self, a, b):
        return a > b


class LessThanEqualFilter(NumberBaseFilter):
    def op(self, a, b):
        return a <= b


class GreaterThanEqualFilter(NumberBaseFilter):
    def op(self, a, b):
        return a >= b


class InFilter(BaseFilter):
    min_items = 0

    def _schema(self):
        return {
            "type": "array",
            "minItems": self.min_items,
            "uniqueItems": True,
            "items": self.field.response  # NOTE: None is valid.
        }

    def _convert(self, items):
        return [self.field.convert(item) for item in items]

    def op(self, a, b):
        return a in b


class ContainsFilter(BaseFilter):
    def _schema(self):
        return self.field.container.response

    def op(self, a, b):
        return hasattr(a, '__iter__') and b in a


class StringBaseFilter(BaseFilter):
    def _schema(self):
        return {
            "type": "string",
            "minLength": 1
        }


class StringContainsFilter(StringBaseFilter):
    def op(self, a, b):
        return a and b in a


class StringIContainsFilter(BaseFilter):
    def _schema(self):
        return {
            "type": "string",
            "minLength": 1
        }

    def op(self, a, b):
        return a and b.lower() in a.lower()


class StartsWithFilter(StringBaseFilter):
    def op(self, a, b):
        return a.startswith(b)


class IStartsWithFilter(StringBaseFilter):
    def op(self, a, b):
        return a.lower().startswith(b.lower())


class EndsWithFilter(StringBaseFilter):
    def op(self, a, b):
        return a.endswith(b)


class IEndsWithFilter(StringBaseFilter):
    def op(self, a, b):
        return a.lower().endswith(b.lower())


class DateBetweenFilter(BaseFilter):
    def _schema(self):
        return {
            "type": "array",
            "minItems": 2,
            "maxItems": 2,
            "items": self.field.response
        }

    def _convert(self, value):
        before, after = value
        return self.field.convert(before), self.field.convert(after)

    def op(self, a, b):
        before, after = b
        return before <= a <= after


EQUALITY_FILTER_NAME = 'eq'

FILTER_NAMES = (
    (EqualFilter, None),
    (EqualFilter, 'eq'),
    (NotEqualFilter, 'ne'),
    (LessThanFilter, 'lt'),
    (LessThanEqualFilter, 'lte'),
    (GreaterThanFilter, 'gt'),
    (GreaterThanEqualFilter, 'gte'),
    (InFilter, 'in'),
    (ContainsFilter, 'contains'),
    (StringContainsFilter, 'contains'),
    (StringIContainsFilter, 'icontains'),
    (StartsWithFilter, 'startswith'),
    (IStartsWithFilter, 'istartswith'),
    (EndsWithFilter, 'endswith'),
    (IEndsWithFilter, 'iendswith'),
    (DateBetweenFilter, 'between'),
)

FILTERS_BY_TYPE = (
    (Boolean, (
        EqualFilter,
        NotEqualFilter,
        InFilter
    )),
    (Integer, (
        EqualFilter,
        NotEqualFilter,
        LessThanFilter,
        LessThanEqualFilter,
        GreaterThanFilter,
        GreaterThanEqualFilter,
        InFilter,
    )),
    (Number, (
        EqualFilter,
        NotEqualFilter,
        LessThanFilter,
        LessThanEqualFilter,
        GreaterThanFilter,
        GreaterThanEqualFilter,
        InFilter,
    )),
    (String, (
        EqualFilter,
        NotEqualFilter,
        StringContainsFilter,
        StringIContainsFilter,
        StartsWithFilter,
        IStartsWithFilter,
        EndsWithFilter,
        IEndsWithFilter,
        InFilter,
    )),
    (Date, (
        EqualFilter,
        NotEqualFilter,
        LessThanFilter,
        LessThanEqualFilter,
        GreaterThanFilter,
        GreaterThanEqualFilter,
        DateBetweenFilter,
        InFilter,
    )),
    (DateTime, (
        EqualFilter,
        NotEqualFilter,
        LessThanFilter,
        LessThanEqualFilter,
        GreaterThanFilter,
        GreaterThanEqualFilter,
        DateBetweenFilter,
    )),
    (DateString, (
        EqualFilter,
        NotEqualFilter,
        LessThanFilter,
        LessThanEqualFilter,
        GreaterThanFilter,
        GreaterThanEqualFilter,
        DateBetweenFilter,
        InFilter,
    )),
    (DateTimeString, (
        EqualFilter,
        NotEqualFilter,
        LessThanFilter,
        LessThanEqualFilter,
        GreaterThanFilter,
        GreaterThanEqualFilter,
        DateBetweenFilter
    )),
    (Array, (
        ContainsFilter,
    )),
    (ToOne, (
        EqualFilter,
        NotEqualFilter,
        InFilter,
    )),
    (ToMany, (
        ContainsFilter,
    )),
)


class Condition(object):
    def __init__(self, attribute, filter, value):
        self.attribute = attribute
        self.filter = filter
        self.value = value

    def __call__(self, item):
        return self.filter.op(get_value(self.attribute, item, None), self.value)


def _get_names_for_filter(filter, filter_names=FILTER_NAMES):
    for f, name in filter_names:
        if f == filter:
            yield name

def filters_for_fields(fields,
                       filters_expression,
                       filter_names=FILTER_NAMES,
                       filters_by_type=FILTERS_BY_TYPE):
    """
    The filters-expression can be a :class:`bool` or a :class:`dict` keyed by field names. The values of the
    :class:`dict` can be either a :class:`bool` or a list of filter names. The `'*'` attribute is a wildcard
    for any remaining field names.

    For example, the following allows all filters:

    ::

        filters = True

    The following allows filtering on the ``"name"`` field:

    ::

        filters = {
            "name": True
        }

    The following allows filtering by equals and not equals on the ``"name"`` field:

    ::

        filters = {
            "name": ['eq', 'ne']
        }

    In addition it is also possible to specify custom filters this way:

    ::

        filters = {
            "name": {
                'text': MyTextFilter
            },
            "*": True
        }

    :param dict fields:
    :param filters_expression:
    :return: a dict of dicts with field names, filter names and filters
    """
    filters = {}
    filters_by_type = dict(filters_by_type)

    for field_name, field in fields.items():
        try:
            field_filters = {
                name: filter
                for filter in filters_by_type[field.__class__]
                for name in _get_names_for_filter(filter, filter_names)
            }
        except KeyError:
            continue

        if isinstance(filters_expression, dict):
            try:
                field_expression = filters_expression[field_name]
            except KeyError:
                try:
                    field_expression = filters_expression['*']
                except KeyError:
                    continue

            # if isinstance(field_expression, dict):
            #     field_filters = field_expression
            if isinstance(field_expression, (list, tuple)):
                field_filters = {
                    name: filter
                    for name, filter in field_filters.items()
                    if name in field_expression
                }
            elif field_expression is not True:
                continue
        elif filters_expression is not True:
            continue

        filters[field_name] = field_filters

    return filters


def convert_filters(value, field_filters):
    if isinstance(value, dict) and len(value) == 1:
        filter_name = next(iter(value))

        # search for filters in the format {"$filter": condition}
        if len(filter_name) > 1 and filter_name.startswith('$'):
            filter_name = filter_name[1:]

            for filter in field_filters.values():
                if filter_name == filter.name:
                    return filter.convert(value)

    filter = field_filters[None]
    return filter.convert(value)
