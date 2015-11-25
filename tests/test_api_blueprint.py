from flask import Blueprint
from flask_potion import Api
from flask_potion.contrib.memory.manager import MemoryManager
from flask_potion.resource import ModelResource
from tests import BaseTestCase


class BlueprintApiTestCase(BaseTestCase):

    def test_api_blueprint(self):
        class SampleResource(ModelResource):

            class Meta:
                name = "samples"
                model = "samples"
                manager = MemoryManager

        api_bp = Blueprint("potion_blueprint", __name__.split(".")[0])
        api = Api(api_bp)
        api.add_resource(SampleResource)

        # Register Blueprint
        self.app.register_blueprint(api_bp)
        response = self.client.get("/samples")
        self.assert200(response)

    def test_multiple_api_blueprints(self):
        class SampleResource(ModelResource):

            class Meta:
                name = "samples"
                model = "samples"
                manager = MemoryManager

        class SampleResource2(ModelResource):

            class Meta:
                name = "samples2"
                model = "samples"
                manager = MemoryManager

        api_bp = Blueprint("potion_blueprint", __name__.split(".")[0])
        api = Api(api_bp)
        api.add_resource(SampleResource)

        api_bp2 = Blueprint("potion_blueprint2", __name__.split(".")[0])
        api2 = Api(api_bp2)
        api2.add_resource(SampleResource2)

        # Register Blueprint
        self.app.register_blueprint(api_bp)
        self.app.register_blueprint(api_bp2)

        response = self.client.get("/samples")
        self.assert200(response)

        response = self.client.get("/samples2")
        self.assert200(response)
