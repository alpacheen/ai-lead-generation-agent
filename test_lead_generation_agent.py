import unittest
from lead_generation_agent import LeadGenerationAgent
import os
import json

class TestLeadGenerationAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a test configuration file
        cls.test_config = {
            "database_file": "test_leads.db",
            "email_template_directory": "email_templates",
            "email_sender": "test@example.com",
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "email_username": "test_user",
            "email_password": "test_password",
            "twilio_account_sid": "test_sid",
            "twilio_auth_token": "test_token",
            "twilio_phone_number": "+1234567890",
            "crm_api_url": "https://api.testcrm.com",
            "crm_api_key": "test_api_key"
        }
        with open('test_config.json', 'w') as f:
            json.dump(cls.test_config, f)

    @classmethod
    def tearDownClass(cls):
        # Remove the test configuration file and database
        os.remove('test_config.json')
        os.remove(cls.test_config['database_file'])

    def setUp(self):
        self.agent = LeadGenerationAgent('test_config.json')

    def test_generate_lead(self):
        lead_id = self.agent.generate_lead({"name": "Test User", "email": "test@example.com", "company": "Test Corp"})
        self.assertIsNotNone(lead_id)
        self.assertTrue(lead_id.startswith("LEAD_"))

    def test_qualify_lead(self):
        lead_id = self.agent.generate_lead({"name": "Test User", "email": "test@example.com", "company": "Test Corp"})
        qualification = self.agent.qualify_lead(lead_id, {"budget": True, "authority": True, "need": True, "timeline": True})
        self.assertEqual(qualification, "Priority Lead")

    def test_score_lead(self):
        lead_id = self.agent.generate_lead({"name": "Test User", "email": "test@example.com", "company": "Test Corp"})
        score = self.agent.score_lead(lead_id)
        self.assertIsInstance(score, int)
        self.assertTrue(0 <= score <= 100)

    def test_generate_report(self):
        self.agent.generate_lead({"name": "Test User 1", "email": "test1@example.com", "company": "Test Corp 1"})
        self.agent.generate_lead({"name": "Test User 2", "email": "test2@example.com", "company": "Test Corp 2"})
        report = self.agent.generate_detailed_report()
        self.assertIn('total_leads', report)
        self.assertIn('score_distribution', report)
        self.assertIn('qualification_distribution', report)
        self.assertIn('contact_success_rate', report)

if __name__ == '__main__':
    unittest.main()