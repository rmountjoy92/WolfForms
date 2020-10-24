# WolfForms

Stupid simple form validation for Flask and more.
---

## Installation
```bash
pip install wolf-forms
```

## Usage

Initialize WolfForms class (without Flask)
```python
from wolf_forms import WolfForms
wolf_forms = WolfForms()
```

Initialize WolfForms class (with Flask)
```python
from flask import Flask
from wolf_forms import WolfForms

app = Flask(__name__)
wolf_forms = WolfForms(app)
```
Or for factory pattern
```python
from flask import Flask
from wolf_forms import WolfForms

wolf_forms = WolfForms()

def create_app():
    app = Flask(__name__)
    wolf_forms.init_app(app)
```
Create a form
```python
wolf_forms.add_form(
    "test_form",
    validators=[
        {'test_string': {"type": "str", "required": True}},
        {'test_int': {"type": "int", "required": True}},
    ]
)
```

In your template
```html
<form>
    {{ wf_csrf_token }}
    <input name="test_string">
    <input name="test_int">
</form>
```

When submitting the form
```python
form = wolf_forms.parse_form(form, 'test_form')
response = wolf_forms.validate(form, 'test_form', csrf=True)
```

Check response for errors
```python
print(response)
if not response.valid:
    for error in response.errors:
        print(error)
        print(error.error)
        print(error.field_name)
        print(error.validate_function)
        print(error.value)
```

## A Minimal Example
```python
from flask import Flask, render_template_string, request
from wolf_forms import WolfForms

app = Flask(__name__)
wolf_forms = WolfForms(app)

wolf_forms.add_form(
    "test_form",
    validators=[
        {'test_string': {"type": "str", "required": True}},
    ]
)

@app.route('/', methods=['GET'])
def index():
    return render_template_string(
    """
    <form id="testForm">
        {{ wf_csrf_token }}
        <input name="test_string">
        <button type="submit" role="button">Submit</button>
    </form>
    <script>
        const formUrl = "{{ url_for('accept_form') }}";
        let testForm = document.getElementById('testForm');
        testForm.addEventListener('submit', function (e) {
            e.preventDefault();
            fetch(formUrl, {
                method: "post",
                body: new FormData(testForm),
            }).then((r) => r.text()).then((r) => alert(r))
        });
    </script>
    """
    )

@app.route('/accept_form', methods=['POST'])
def accept_form():
    form = wolf_forms.parse_form(request.form, 'test_form')
    response = wolf_forms.validate(form, 'test_form', csrf=True)
    print(response)
    if not response.valid:
        for error in response.errors:
            print(error)
    return str(response)

if __name__ == "__main__":
    app.run()
```

