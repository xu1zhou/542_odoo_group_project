from odoo.tests import tagged
from odoo.tests.common import SavepointCase


@tagged("test_01", "post_install", "-at_install")
class TestVehicleDelete(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.Brand = cls.env["fleet.vehicle.model.brand"]
        cls.VehicleModel = cls.env["fleet.vehicle.model"]
        cls.Vehicle = cls.env["fleet.vehicle"]

        cls.brand = cls.Brand.create({"name": "Delete Test Brand"})
        cls.model = cls.VehicleModel.create({
            "name": "Delete Test Model",
            "brand_id": cls.brand.id,
        })

    def test_01_vehicle_delete(self):
        """Create a vehicle and verify it can be deleted successfully."""
        vehicle = self.Vehicle.create({
            "model_id": self.model.id,
            "license_plate": "DEL-001",
        })
        vehicle_id = vehicle.id
        self.assertTrue(vehicle_id)

        vehicle.unlink()

        remaining = self.Vehicle.search([("id", "=", vehicle_id)])
        self.assertFalse(remaining, "Vehicle should no longer exist after deletion.")
