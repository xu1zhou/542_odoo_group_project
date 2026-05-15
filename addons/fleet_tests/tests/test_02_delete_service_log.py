from odoo.tests import tagged
from odoo.tests.common import SavepointCase
from odoo import fields


@tagged("test_02", "post_install", "-at_install")
class TestDeleteServiceLog(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.Brand = cls.env["fleet.vehicle.model.brand"]
        cls.VehicleModel = cls.env["fleet.vehicle.model"]
        cls.Vehicle = cls.env["fleet.vehicle"]
        cls.ServiceType = cls.env["fleet.service.type"]
        cls.ServiceLog = cls.env["fleet.vehicle.log.services"]

        cls.brand = cls.Brand.create({"name": "SvcDel Brand"})
        cls.model = cls.VehicleModel.create({
            "name": "SvcDel Model",
            "brand_id": cls.brand.id,
        })
        cls.vehicle = cls.Vehicle.create({
            "model_id": cls.model.id,
            "license_plate": "SVC-DEL",
        })
        cls.service_type = cls.ServiceType.create({
            "name": "Tire Rotation",
            "category": "service",
        })

    def test_02_delete_service_log(self):
        """Create a service log entry and verify it can be deleted successfully."""
        log = self.ServiceLog.create({
            "vehicle_id": self.vehicle.id,
            "service_type_id": self.service_type.id,
            "amount": 49.99,
            "date": fields.Date.today(),
            "description": "Test service log to be deleted",
        })
        log_id = log.id
        self.assertTrue(log_id)
        self.assertEqual(log.vehicle_id, self.vehicle)

        log.unlink()

        remaining = self.ServiceLog.search([("id", "=", log_id)])
        self.assertFalse(remaining, "Service log should no longer exist after deletion.")
