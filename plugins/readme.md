# PLUGINS

[READ MORE](https://airflow.apache.org/docs/apache-airflow/2.3.1/plugins.html)

[EXAMPLE PLUGIN](https://github.com/rssanders3/airflow-admin-tools-plugin)

## Interface

To create a plugin you will need to derive the airflow.plugins_manager.AirflowPlugin class and reference the objects you want to plug into Airflow. Here's what the class you need to derive looks like:

```python
class AirflowPlugin:
    # The name of your plugin (str)
    name = None
    # A list of class(es) derived from BaseHook
    hooks = []
    # A list of references to inject into the macros namespace
    macros = []
    # A list of Blueprint object created from flask.Blueprint. For use with the flask_appbuilder based GUI
    flask_blueprints = []
    # A list of dictionaries containing FlaskAppBuilder BaseView object and some metadata. See example below
    appbuilder_views = []
    # A list of dictionaries containing kwargs for FlaskAppBuilder add_link. See example below
    appbuilder_menu_items = []
    # A callback to perform actions when airflow starts and the plugin is loaded.
    # NOTE: Ensure your plugin has *args, and **kwargs in the method definition
    #   to protect against extra parameters injected into the on_load(...)
    #   function in future changes
    def on_load(*args, **kwargs):
        # ... perform Plugin boot actions
        pass

    # A list of global operator extra links that can redirect users to
    # external systems. These extra links will be available on the
    # task page in the form of buttons.
    #
    # Note: the global operator extra link can be overridden at each
    # operator level.
    global_operator_extra_links = []

    # A list of operator extra links to override or add operator links
    # to existing Airflow Operators.
    # These extra links will be available on the task page in form of
    # buttons.
    operator_extra_links = []

    # A list of timetable classes to register so they can be used in DAGs.
    timetables = []

    # A list of Listeners that plugin provides. Listeners can register to
    # listen to particular events that happen in Airflow, like
    # TaskInstance state changes. Listeners are python modules.
    listeners = []
```

You can derive it by inheritance (please refer to the example below). In the example, all options have been defined as class attributes, but you can also define them as properties if you need to perform additional initialization. Please note name inside this class must be specified.

Make sure you restart the webserver and scheduler after making changes to plugins so that they take effect.


Example

The code below defines a plugin that injects a set of dummy object definitions in Airflow.

```python
# This is the class you derive to create a plugin
from airflow.plugins_manager import AirflowPlugin

from flask import Blueprint
from flask_appbuilder import expose, BaseView as AppBuilderBaseView

# Importing base classes that we need to derive
from airflow.hooks.base import BaseHook
from airflow.providers.amazon.aws.transfers.gcs_to_s3 import GCSToS3Operator

# Will show up in Connections screen in a future version
class PluginHook(BaseHook):
    pass


# Will show up under airflow.macros.test_plugin.plugin_macro
# and in templates through {{ macros.test_plugin.plugin_macro }}
def plugin_macro():
    pass


# Creating a flask blueprint to integrate the templates and static folder
bp = Blueprint(
    "test_plugin",
    __name__,
    template_folder="templates",  # registers airflow/plugins/templates as a Jinja template folder
    static_folder="static",
    static_url_path="/static/test_plugin",
)

# Creating a flask appbuilder BaseView
class TestAppBuilderBaseView(AppBuilderBaseView):
    default_view = "test"

    @expose("/")
    def test(self):
        return self.render_template("test_plugin/test.html", content="Hello galaxy!")


# Creating a flask appbuilder BaseView
class TestAppBuilderBaseNoMenuView(AppBuilderBaseView):
    default_view = "test"

    @expose("/")
    def test(self):
        return self.render_template("test_plugin/test.html", content="Hello galaxy!")


v_appbuilder_view = TestAppBuilderBaseView()
v_appbuilder_package = {
    "name": "Test View",
    "category": "Test Plugin",
    "view": v_appbuilder_view,
}

v_appbuilder_nomenu_view = TestAppBuilderBaseNoMenuView()
v_appbuilder_nomenu_package = {"view": v_appbuilder_nomenu_view}

# Creating flask appbuilder Menu Items
appbuilder_mitem = {
    "name": "Google",
    "href": "https://www.google.com",
    "category": "Search",
}
appbuilder_mitem_toplevel = {
    "name": "Apache",
    "href": "https://www.apache.org/",
}


# Defining the plugin class
class AirflowTestPlugin(AirflowPlugin):
    name = "test_plugin"
    hooks = [PluginHook]
    macros = [plugin_macro]
    flask_blueprints = [bp]
    appbuilder_views = [v_appbuilder_package, v_appbuilder_nomenu_package]
    appbuilder_menu_items = [appbuilder_mitem, appbuilder_mitem_toplevel]
```