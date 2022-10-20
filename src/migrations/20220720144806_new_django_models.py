from bson import ObjectId

from mongodb_migrations.base import BaseMigration


class Migration(BaseMigration):
    def upgrade(self):
        # Resource version needs an ID
        resources = self.db.wstore_resource.find()

        for resource in resources:
            for version in resource['old_versions']:
                version['_id'] = ObjectId()

            self.db.wstore_resource.save()

        # Contract changes offering from ForeignKey to Char (Remove ObjectID)
        orders = self.db.wstore_order.find()

        for order in orders:
            for contract in order['contracts']:
                contract['offering'] = str(contract['offering'])

            self.db.wstore_order.save(order)

    def downgrade(self):
        resources = self.db.wstore_resource.find()

        for resource in resources:
            for version in resource['old_versions']:
                del version['_id']

            self.db.wstore_resource.save()

        orders = self.db.wstore_order.find()

        for order in orders:
            for contract in order['contracts']:
                contract['offering'] = ObjectId(contract['offering'])

            self.db.wstore_order.save(order)
