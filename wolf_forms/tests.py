import unittest
from time import sleep
from . import WolfForms, custom_validate_function, Response, Error


class TestWolfForms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wolf_forms = WolfForms()

    def test_csrf_token(self):
        token = self.wolf_forms.generate_csrf()
        self.assertTrue(self.wolf_forms.validate_token(token))
        form = {"csrf_token": token}
        response = self.wolf_forms.validate(form, None, csrf=True)
        self.assertTrue(len(response.errors) == 0 and response.valid is True)
        form = {"csrf_token": "fish"}
        response = self.wolf_forms.validate(form, None, csrf=True)
        self.assertTrue(response.errors[0].error == "Failed to validate csrf token")

    def test_expire_csrf(self):
        wolf_forms = WolfForms()
        token = wolf_forms.generate_csrf(ttl=1)
        self.assertTrue(wolf_forms.validate_token(token))
        sleep(1)
        self.assertFalse(wolf_forms.validate_token(token))

        wolf_forms = WolfForms(csrf_ttl=1)
        token = wolf_forms.generate_csrf()
        self.assertTrue(wolf_forms.validate_token(token))
        sleep(1)
        self.assertFalse(wolf_forms.validate_token(token))

    def test_add_forms(self):
        self.assertRaises(Exception, self.wolf_forms.add_form, 1, None)

        self.assertRaises(Exception, self.wolf_forms.add_form, "test", None)

        validators = []
        self.assertRaises(Exception, self.wolf_forms.add_form, "test", validators)

        validators = [1]
        self.assertRaises(Exception, self.wolf_forms.add_form, "test", validators)

        validators = [{1: None}]
        self.assertRaises(Exception, self.wolf_forms.add_form, "test", validators)

        validators = [{"test": None}]
        self.assertRaises(Exception, self.wolf_forms.add_form, "test", validators)

        validators = [{"test": {"type": "str"}}]
        self.wolf_forms.add_form("test", validators)
        self.assertTrue(self.wolf_forms.forms["test"][0]["test"]["type"] == "str")

    def test_parse_form(self):
        form = {
            "test_string": 1,
            "test_int": "1",
            "test_float": "1",
            "test_list": "1,2,3",
            "test_dict": '{"hello": "world"}',
            "test_bool": "true",
        }
        validators = [
            {"test_string": {"type": "str"}},
            {"test_int": {"type": "int"}},
            {"test_float": {"type": "float"}},
            {"test_list": {"type": "list"}},
            {"test_dict": {"type": "dict"}},
            {"test_bool": {"type": "bool"}},
        ]
        self.wolf_forms.add_form("test_form", validators)
        form = self.wolf_forms.parse_form(form, "test_form")
        self.assertIsInstance(form.get("test_string"), str)
        self.assertIsInstance(form.get("test_int"), int)
        self.assertIsInstance(form.get("test_float"), float)
        self.assertIsInstance(form.get("test_list"), list)
        self.assertTrue(len(form.get("test_list")) == 3)
        self.assertTrue(form["test_dict"]["hello"] == "world")
        self.assertTrue(form.get("test_bool"))

        self.wolf_forms = WolfForms()
        form = {
            "test_string": 9,
            "test_int": "fish",
            "test_float": "<3",
            "test_list": "item",
            "test_dict": "fish",
            "test_bool": "ham",
        }
        validators = [
            {"test_string": {"type": "str", "required": True}},
            {"test_int": {"type": "int", "required": True}},
            {"test_float": {"type": "float", "required": True}},
            {"test_list": {"type": "list", "required": True}},
            {"test_dict": {"type": "dict", "required": True}},
            {"test_bool": {"type": "bool", "required": True}},
        ]
        self.wolf_forms.add_form("test_form", validators)
        self.assertRaises(Exception, self.wolf_forms.parse_form, form, "test_form")
        form["test_int"] = "1"
        self.assertRaises(Exception, self.wolf_forms.parse_form, form, "test_form")
        form["test_float"] = "1"
        self.assertRaises(Exception, self.wolf_forms.parse_form, form, "test_form")
        form["test_dict"] = '{"hello": "world"}'
        self.assertRaises(Exception, self.wolf_forms.parse_form, form, "test_form")
        form["test_bool"] = "true"
        self.wolf_forms.parse_form(form, "test_form")

    def test_invalid_method(self):
        # test invalid validate function
        form = {"test": "test"}
        validators = [
            {"test": {"fish": "str"}},
        ]
        self.wolf_forms.add_form("test_form", validators)
        response = self.wolf_forms.validate(form, "test_form")
        self.assertTrue(response.errors[0].validate_function == "fish")

    def test_required_method(self):
        # test required validate function
        form = {"test": "test"}
        validators = [{"testy": {"required": True}}]
        self.wolf_forms.add_form("test_form", validators)
        response = self.wolf_forms.validate(form, "test_form")
        self.assertTrue(response.errors[0].validate_function == "required")

    def test_type_method(self):
        # test _type validate function
        form = {
            "test_string": "string",
            "test_int": 1,
            "test_float": 1.0,
            "test_list": ["hi"],
            "test_dict": {"hello": "world"},
            "test_bool": True,
        }
        validators = [
            {"test_string": {"type": "str"}},
            {"test_int": {"type": "int"}},
            {"test_float": {"type": "float"}},
            {"test_list": {"type": "list"}},
            {"test_dict": {"type": "dict"}},
            {"test_bool": {"type": "bool"}},
        ]
        self.wolf_forms.add_form("test_form", validators)
        response = self.wolf_forms.validate(form, "test_form")
        self.assertTrue(len(response.errors) == 0 and response.valid is True)

        form = {
            "test_string": 1,
            "test_int": "fish",
            "test_float": "fish",
            "test_list": "fish",
            "test_dict": "fish",
            "test_bool": "fish",
        }
        validators = [
            {"test_string": {"type": "str"}},
            {"test_int": {"type": "int"}},
            {"test_float": {"type": "float"}},
            {"test_list": {"type": "list"}},
            {"test_dict": {"type": "dict"}},
            {"test_bool": {"type": "bool"}},
        ]
        self.wolf_forms.add_form("test_form", validators)
        response = self.wolf_forms.validate(form, "test_form")
        self.assertTrue(len(response.errors) == 6 and response.valid is False)

    def test_regex_search_method(self):
        # test regex_search validate function
        form = {"test": "hello"}
        validators = [
            {"test": {"regex_search": "hello"}},
        ]
        self.wolf_forms.add_form("test_form", validators)
        response = self.wolf_forms.validate(form, "test_form")
        self.assertTrue(len(response.errors) == 0 and response.valid is True)
        form = {"test": "fish"}
        response = self.wolf_forms.validate(form, "test_form")
        self.assertTrue(response.errors[0].validate_function == "regex_search")

    def test_min_length_method(self):
        # test min_length validate function
        form = {"test": "a"}
        validators = [
            {"test": {"min_length": 1}},
        ]
        self.wolf_forms.add_form("test_form", validators)
        response = self.wolf_forms.validate(form, "test_form")
        self.assertTrue(len(response.errors) == 0 and response.valid is True)
        form = {"test": ""}
        response = self.wolf_forms.validate(form, "test_form")
        self.assertTrue(response.errors[0].validate_function == "min_length")

    def test_max_length_method(self):
        # test max_length validate function
        form = {"test": "a"}
        validators = [
            {"test": {"max_length": 1}},
        ]
        self.wolf_forms.add_form("test_form", validators)
        response = self.wolf_forms.validate(form, "test_form")
        self.assertTrue(len(response.errors) == 0 and response.valid is True)
        form = {"test": "ab"}
        response = self.wolf_forms.validate(form, "test_form")
        self.assertTrue(response.errors[0].validate_function == "max_length")

    def test_expression_method(self):
        # test expression validate function
        form = {"test": "a"}
        validators = [
            {"test": {"expression": "field_value == 'a'"}},
        ]
        self.wolf_forms.add_form("test_form", validators)
        response = self.wolf_forms.validate(form, "test_form")
        self.assertTrue(len(response.errors) == 0 and response.valid is True)
        form = {"test": "b"}
        response = self.wolf_forms.validate(form, "test_form")
        self.assertTrue(response.errors[0].validate_function == "expression")

    def test_custom_method(self):
        # test custom validate function
        @custom_validate_function(WolfForms)
        def is_groovy(form, response, field_name, validate_function, value):
            response = Response()
            field_value = form.get(field_name)
            if "groovy" not in field_value and value is True:
                response.valid = False
                response.errors.append(
                    Error(
                        "Value is not groovy",
                        field_name=field_name,
                        validate_function=validate_function,
                        value=value,
                    )
                )
            return response

        form = {"test": "I am groovy"}
        validators = [
            {"test": {"is_groovy": True}},
        ]
        self.wolf_forms.add_form("test_form", validators)
        response = self.wolf_forms.validate(form, "test_form")
        self.assertTrue(len(response.errors) == 0 and response.valid is True)
        form = {"test": "I am cool"}
        response = self.wolf_forms.validate(form, "test_form")
        self.assertTrue(response.errors[0].validate_function == "is_groovy")
