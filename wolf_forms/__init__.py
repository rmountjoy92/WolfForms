"""

██╗    ██╗ ██████╗ ██╗     ███████╗    ███████╗ ██████╗ ██████╗ ███╗   ███╗███████╗
██║    ██║██╔═══██╗██║     ██╔════╝    ██╔════╝██╔═══██╗██╔══██╗████╗ ████║██╔════╝
██║ █╗ ██║██║   ██║██║     █████╗      █████╗  ██║   ██║██████╔╝██╔████╔██║███████╗
██║███╗██║██║   ██║██║     ██╔══╝      ██╔══╝  ██║   ██║██╔══██╗██║╚██╔╝██║╚════██║
╚███╔███╔╝╚██████╔╝███████╗██║         ██║     ╚██████╔╝██║  ██║██║ ╚═╝ ██║███████║
 ╚══╝╚══╝  ╚═════╝ ╚══════╝╚═╝         ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝

Stupid simple form validation for Flask and more.

Version: 0.1

Author: Ross Mountjoy

Github: https://github.com/rmountjoy92

License: MIT
"""
import re
import json
from markupsafe import Markup
from secrets import token_hex
from functools import wraps
from time import sleep
from threading import Thread
from flask_bcrypt import Bcrypt


class WolfForms:
    def __init__(self, app=None, csrf_ttl=None):
        self.app = None
        self.bcrypt = Bcrypt()
        self.csrf_tokens = []
        self.hashed_tokens = {}
        self.csrf_ttl = csrf_ttl or 600
        self.forms = {}

        self.init_app(app)

    def init_app(self, app):
        if app:
            self.app = app
            self.bcrypt.init_app(app)

            @app.context_processor
            def provide_csrf_input_html():
                html = (
                    f'<input name="csrf_token" value="{self.generate_csrf()}" '
                    f'style="display: none">'
                )
                return dict(wf_csrf_token=Markup(html))

    def generate_csrf(self, ttl=None):
        token_id = len(self.csrf_tokens) + 1
        self.csrf_tokens.append(token_id)
        csrf_token = f"{token_hex(16)}"
        hashed_csrf_token = self.bcrypt.generate_password_hash(csrf_token)
        self.hashed_tokens[token_id] = hashed_csrf_token
        proc = Thread(target=self.expire_csrf, args=[token_id, ttl], daemon=True)
        proc.start()
        return f"{token_id}:{csrf_token}"

    def expire_csrf(self, token_id, ttl):
        sleep(ttl or self.csrf_ttl)
        self.csrf_tokens.remove(token_id)
        del self.hashed_tokens[token_id]

    def validate_token(self, token):
        try:
            token_id = int(token.split(":")[0])
        except ValueError:
            return False
        try:
            token = token.split(":")[1]
        except IndexError:
            return False

        try:
            check_hash = self.bcrypt.check_password_hash(
                self.hashed_tokens[token_id], token
            )
        except KeyError:
            return False
        return check_hash

    def add_form(self, form_name, validators):
        if not isinstance(form_name, str):
            raise Exception("form_name must be a string")

        if not isinstance(validators, list):
            raise Exception("Validators must be a list")

        if len(validators) < 1:
            raise Exception("You must have at least one validator for the form")

        for validator in validators:
            if not isinstance(validator, dict):
                raise Exception("Each validator must be a dict")
            field_name = f"{next(iter(validator))}"
            if not isinstance(field_name, str):
                raise Exception("field_name must be a string")
            if not isinstance(validator[field_name], dict):
                raise Exception("Validator field methods must be a dict")

        self.forms[form_name] = validators

    def parse_form(self, form, form_name):
        parsed_form = {}
        for key, value in form.items():
            parsed_form[key] = value

        validators = self.forms[form_name]
        for validator in validators:
            field_name = f"{next(iter(validator))}"
            if parsed_form[field_name] or validator[field_name].get("required"):
                try:
                    if validator[field_name].get("type"):
                        if validator[field_name]["type"] == "dict":
                            parsed_form[field_name] = json.loads(
                                parsed_form[field_name]
                            )
                        if validator[field_name]["type"] == "list":
                            parsed_form[field_name] = parsed_form[field_name].split(",")

                        if validator[field_name]["type"] == "bool":
                            if parsed_form[field_name].lower() == "true":
                                parsed_form[field_name] = True
                            elif parsed_form[field_name].lower() == "false":
                                parsed_form[field_name] = False
                            else:
                                raise ValueError(
                                    f"Could not convert {parsed_form[field_name]} to bool"
                                )
                        else:
                            parsed_form[field_name] = py_types[
                                validator[field_name]["type"]
                            ](parsed_form[field_name])
                except Exception as e:
                    raise Exception(f"Could not parse {field_name}, error was: {e}")
        return parsed_form

    def validate(self, form, form_name, validators=None, csrf=False):
        response = Response()
        if not validators:
            validators = []

        if form_name:
            try:
                validators = validators + self.forms[form_name]
            except KeyError:
                response.valid = False
                response.errors.append(
                    Error(error=f"Form: {form_name} not found in configured forms")
                )
                return response

        for validator in validators:
            field_name = f"{next(iter(validator))}"
            try:
                form[field_name]
            except KeyError:
                form[field_name] = ""

            for validate_function, value in validator.get(field_name, {}).items():
                if validate_function == "type":
                    validate_function = "_type"
                validate_class_method = getattr(
                    self, validate_function, self.class_method_not_found
                )
                response = validate_class_method(
                    form, response, field_name, validate_function, value
                )

        if csrf:
            if not self.validate_token(form.get("csrf_token", "!")):
                response.valid = False
                response.errors.append(Error(error="Failed to validate csrf token"))
                return response
        return response

    @staticmethod
    def class_method_not_found(form, response, field_name, validate_function, value):
        response.valid = False
        response.errors.append(
            Error(
                error=f"{validate_function} is not a valid validate function",
                field_name=field_name,
                validate_function=validate_function,
                value=value,
            )
        )
        return response

    @staticmethod
    def required(form, response, field_name, validate_function, value):
        if len(form.get(field_name, "")) < 1 and value is True:
            response.valid = False
            response.errors.append(
                Error(
                    error=f"{field_name} is required",
                    field_name=field_name,
                    validate_function=validate_function,
                    value=value,
                )
            )
        return response

    @staticmethod
    def _type(form, response, field_name, validate_function, value):
        field_value = form.get(field_name, None)
        error = Error(
            field_name=field_name, validate_function=validate_function, value=value
        )

        for py_type_str, py_type_obj in py_types.items():
            if value == py_type_str and not isinstance(field_value, py_type_obj):
                response.valid = False
                error.error = f"{field_name} is not {py_type_str}"
                response.errors.append(error)
        if value == "email":
            regex = "^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$"
            if not re.search(regex, field_value):
                response.valid = False
                error.error = f"{field_name} is not a valid email address"
                response.errors.append(error)
        return response

    @staticmethod
    def regex_search(form, response, field_name, validate_function, value):
        if not re.search(value, form.get(field_name)):
            response.valid = False
            response.errors.append(
                Error(
                    error=f"{field_name} failed regex search",
                    field_name=field_name,
                    validate_function=validate_function,
                    value=value,
                )
            )
        return response

    @staticmethod
    def min_length(form, response, field_name, validate_function, value):
        if len(form.get(field_name)) < value:
            response.valid = False
            response.errors.append(
                Error(
                    error=f"{field_name} must be at least [{value}] characters",
                    field_name=field_name,
                    validate_function=validate_function,
                    value=value,
                )
            )
        return response

    @staticmethod
    def max_length(form, response, field_name, validate_function, value):
        if len(form.get(field_name)) > value:
            response.valid = False
            response.errors.append(
                Error(
                    error=f"{field_name} can't be more than [{value}] characters",
                    field_name=field_name,
                    validate_function=validate_function,
                    value=value,
                )
            )
        return response

    @staticmethod
    def expression(form, response, field_name, validate_function, value):
        field_value = form.get(field_name)
        exp = eval(value)
        if exp is False:
            response.valid = False
            response.errors.append(
                Error(
                    error=f"{field_name} failed the expression [{value}]",
                    field_name=field_name,
                    validate_function=validate_function,
                    value=value,
                )
            )
        return response


# custom validate function decorator
def custom_validate_function(cls):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            return func(*args, **kwargs)

        setattr(cls, func.__name__, wrapper)

    return decorator


class Response:
    def __init__(self, valid=True, errors=None):
        self.valid = valid
        self.errors = errors or []

    def __repr__(self):
        return f"Valid: {self.valid}\nErrors: {len(self.errors)}"


class Error:
    def __init__(self, error=None, field_name=None, validate_function=None, value=None):
        self.error = error
        self.field_name = field_name
        self.validate_function = validate_function
        self.value = value

    def __repr__(self):
        return (
            f"{self.error} in {self.field_name}. {self.validate_function} "
            f"failed to validate using {self.value}"
        )


py_types = {
    "str": str,
    "int": int,
    "float": float,
    "list": list,
    "dict": dict,
    "bool": bool,
}
