from odoo.tests.common import SavepointCase
from odoo import fields


class TestUpdateContractLog(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.Brand = cls.env["fleet.vehicle.model.brand"]
        cls.VehicleModel = cls.env["fleet.vehicle.model"]
        cls.Vehicle = cls.env["fleet.vehicle"]
        cls.ServiceType = cls.env["fleet.service.type"]
        cls.ContractLog = cls.env["fleet.vehicle.log.contract"]

        cls.brand = cls.Brand.create({"name": "Contract Brand"})
        cls.model = cls.VehicleModel.create({
            "name": "Contract Model",
            "brand_id": cls.brand.id,
        })
        cls.vehicle = cls.Vehicle.create({
            "model_id": cls.model.id,
            "license_plate": "CON-001",
        })
        cls.service_type = cls.ServiceType.create({
            "name": "Insurance",
            "category": "contract",
        })

    def test_03_update_contract_log(self):
        """Create a contract log and verify its fields can be updated."""
        Contract = self.ContractLog
        today = fields.Date.today()

        vals = {
            "vehicle_id": self.vehicle.id,
            "cost_subtype_id": self.service_type.id,
            "amount": 300.0,
            "name": "Original Contract",
        }

        # Field names differ across builds; set whichever exists
        if "date_start" in Contract._fields:
            vals["date_start"] = today
        elif "start_date" in Contract._fields:
            vals["start_date"] = today
        elif "date" in Contract._fields:
            vals["date"] = today

        if "date_end" in Contract._fields:
            vals["date_end"] = today
        elif "expiration_date" in Contract._fields:
            vals["expiration_date"] = today
        elif "end_date" in Contract._fields:
            vals["end_date"] = today

        contract = Contract.create(vals)
        self.assertEqual(contract.amount, 300.0)
        self.assertEqual(contract.name, "Original Contract")

        # Update the contract
        contract.write({
            "amount": 450.0,
            "name": "Updated Contract",
        })

        self.assertEqual(contract.amount, 450.0)
        self.assertEqual(contract.name, "Updated Contract")
        self.assertEqual(contract.vehicle_id, self.vehicle)
