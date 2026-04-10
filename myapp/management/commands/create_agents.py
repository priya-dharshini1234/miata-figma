from django.core.management.base import BaseCommand
from django.conf import settings
import bcrypt

class Command(BaseCommand):
    help = 'Create 5 default agent accounts'

    def handle(self, *args, **kwargs):
        db = settings.MONGO_DB
        users_collection = db['users']

        agents = [
            {'username': 'agent001', 'password': 'Miata#@001'},
            {'username': 'agent002', 'password': 'Agent*$002'},
            {'username': 'agent003', 'password': 'Miata&@003'},
            {'username': 'agent004', 'password': 'Agent@#004'},
            {'username': 'agent005', 'password': 'Miata#@005'},
        ]

        for agent in agents:
            existing = users_collection.find_one({'username': agent['username']})
            if existing:
                self.stdout.write(self.style.WARNING(f"Already exists: {agent['username']}"))
                continue

            hashed = bcrypt.hashpw(agent['password'].encode('utf-8'), bcrypt.gensalt())
            users_collection.insert_one({
                'username': agent['username'],
                'password': hashed,
                'role': 'agent',
            })
            self.stdout.write(self.style.SUCCESS(f"✅ Created: {agent['username']}"))

        self.stdout.write(self.style.SUCCESS('Done!'))