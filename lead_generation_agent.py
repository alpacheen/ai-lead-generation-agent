import logging
from datetime import datetime
from typing import Dict, List, Optional
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3
import os
import requests
from twilio.rest import Client
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class LeadGenerationAgent:
    def __init__(self, config_file: str = 'config.json'):
        self.config = self.load_config(config_file)
        self.db_conn = self.initialize_database()
        self.email_templates = self.load_email_templates()
        self.twilio_client = Client(self.config['twilio_account_sid'], self.config['twilio_auth_token'])
        self.lead_scoring_model = self.train_lead_scoring_model()

    def load_config(self, config_file: str) -> Dict:
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"Configuration file {config_file} not found.")
            raise
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON in configuration file {config_file}.")
            raise

    def initialize_database(self) -> sqlite3.Connection:
        try:
            conn = sqlite3.connect(self.config['database_file'])
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leads (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    email TEXT,
                    company TEXT,
                    qualification TEXT,
                    created_at TEXT,
                    score INTEGER
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS contact_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id TEXT,
                    timestamp TEXT,
                    channel TEXT,
                    result TEXT,
                    FOREIGN KEY (lead_id) REFERENCES leads (id)
                )
            ''')
            conn.commit()
            return conn
        except sqlite3.Error as e:
            logging.error(f"Database initialization error: {str(e)}")
            raise

    def load_email_templates(self) -> Dict[str, str]:
        templates = {}
        template_dir = self.config['email_template_directory']
        try:
            for filename in os.listdir(template_dir):
                if filename.endswith('.txt'):
                    with open(os.path.join(template_dir, filename), 'r') as f:
                        template_name = os.path.splitext(filename)[0]
                        templates[template_name] = f.read()
            return templates
        except FileNotFoundError:
            logging.error(f"Email template directory {template_dir} not found.")
            raise
        except IOError as e:
            logging.error(f"Error reading email templates: {str(e)}")
            raise

    def generate_lead(self, contact_info: Dict) -> str:
        lead_id = f"LEAD_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            cursor = self.db_conn.cursor()
            cursor.execute(
                "INSERT INTO leads (id, name, email, company, created_at) VALUES (?, ?, ?, ?, ?)",
                (lead_id, contact_info['name'], contact_info['email'], contact_info['company'], datetime.now().isoformat())
            )
            self.db_conn.commit()
            logging.info(f"New lead generated: {lead_id}")
            return lead_id
        except sqlite3.Error as e:
            logging.error(f"Error generating lead: {str(e)}")
            self.db_conn.rollback()
            raise

    def outbound_contact(self, lead_id: str, channel: str) -> bool:
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
            lead = cursor.fetchone()
            
            if not lead:
                logging.error(f"Lead {lead_id} not found")
                return False

            if channel == 'email':
                success = self.send_email(lead[2], lead[1], 'initial_contact')
            elif channel == 'sms':
                success = self.send_sms(lead_id, "Hello! We'd like to discuss our services with you.")
            else:
                logging.error(f"Invalid channel: {channel}")
                return False

            cursor.execute(
                "INSERT INTO contact_attempts (lead_id, timestamp, channel, result) VALUES (?, ?, ?, ?)",
                (lead_id, datetime.now().isoformat(), channel, 'success' if success else 'failure')
            )
            self.db_conn.commit()
            logging.info(f"Outbound contact made for lead {lead_id} via {channel}")
            return success
        except Exception as e:
            logging.error(f"Error in outbound contact: {str(e)}")
            self.db_conn.rollback()
            return False

    def qualify_lead(self, lead_id: str, criteria: Dict[str, bool]) -> str:
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
            lead = cursor.fetchone()
            
            if not lead:
                logging.error(f"Lead {lead_id} not found")
                return "Not Found"

            if all(criteria.values()):
                qualification = "Priority Lead"
            elif criteria.get("budget") and criteria.get("authority"):
                qualification = "Nurture Queue"
            elif criteria.get("budget"):
                qualification = "Research Queue"
            else:
                qualification = "Disqualified"

            cursor.execute("UPDATE leads SET qualification = ? WHERE id = ?", (qualification, lead_id))
            self.db_conn.commit()
            logging.info(f"Lead {lead_id} qualified as: {qualification}")
            return qualification
        except sqlite3.Error as e:
            logging.error(f"Error qualifying lead: {str(e)}")
            self.db_conn.rollback()
            raise

    def process_eoi(self, lead_id: str, eoi_data: Dict) -> bool:
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
            lead = cursor.fetchone()
            
            if not lead:
                logging.error(f"Lead {lead_id} not found")
                return False

            # In a real scenario, you would process and store the EOI data
            # For this example, we'll just log it
            logging.info(f"EOI processed for lead {lead_id}: {eoi_data}")
            return True
        except Exception as e:
            logging.error(f"Error processing EOI: {str(e)}")
            return False

    def transfer_lead(self, lead_id: str, sales_team_available: bool) -> str:
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
            lead = cursor.fetchone()
            
            if not lead:
                logging.error(f"Lead {lead_id} not found")
                return "Transfer Failed"

            qualification = lead[4]  # Assuming qualification is stored in the 5th column
            
            if qualification == "Priority Lead" and sales_team_available:
                transfer_status = "Live Transfer"
            elif qualification == "Priority Lead":
                transfer_status = "Priority Callback"
            else:
                transfer_status = "Schedule Follow-up"

            # In a real scenario, you would update the lead status in the database
            logging.info(f"Lead {lead_id} transfer status: {transfer_status}")
            return transfer_status
        except Exception as e:
            logging.error(f"Error transferring lead: {str(e)}")
            return "Transfer Failed"

    def train_lead_scoring_model(self):
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT * FROM leads")
            leads = cursor.fetchall()
            
            if not leads:
                logging.warning("No leads available for training the model")
                return None

            # Prepare data for training
            X = []
            y = []
            for lead in leads:
                # Extract features (you may need to adjust this based on your data)
                features = [
                    len(lead[1]),  # Name length as a feature
                    len(lead[2]),  # Email length as a feature
                    len(lead[3]),  # Company name length as a feature
                    self.get_company_size(lead[3]),
                    1 if self.get_company_industry(lead[3]) in ['Technology', 'Finance', 'Healthcare'] else 0
                ]
                X.append(features)
                y.append(1 if lead[4] == "Priority Lead" else 0)  # 1 for Priority Lead, 0 otherwise

            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            model = RandomForestClassifier(n_estimators=100, random_state=42)
            model.fit(X_train_scaled, y_train)

            accuracy = model.score(X_test_scaled, y_test)
            logging.info(f"Lead scoring model trained with accuracy: {accuracy}")

            return (model, scaler)
        except Exception as e:
            logging.error(f"Error training lead scoring model: {str(e)}")
            return None

    def score_lead(self, lead_id: str) -> int:
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
            lead = cursor.fetchone()
            
            if not lead:
                logging.error(f"Lead {lead_id} not found")
                return 0

            if self.lead_scoring_model is None:
                logging.warning("Lead scoring model not available")
                return 0

            model, scaler = self.lead_scoring_model

            features = [
                len(lead[1]),  # Name length as a feature
                len(lead[2]),  # Email length as a feature
                len(lead[3]),  # Company name length as a feature
                self.get_company_size(lead[3]),
                1 if self.get_company_industry(lead[3]) in ['Technology', 'Finance', 'Healthcare'] else 0
            ]

            features_scaled = scaler.transform([features])
            score = int(model.predict_proba(features_scaled)[0][1] * 100)  # Convert probability to a score out of 100

            cursor.execute("UPDATE leads SET score = ? WHERE id = ?", (score, lead_id))
            self.db_conn.commit()

            return score
        except Exception as e:
            logging.error(f"Error scoring lead: {str(e)}")
            return 0

    def get_company_size(self, company_name: str) -> int:
        # In a real scenario, you would use an API or database to get this information
        # For this example, we'll return a random number
        import random
        return random.randint(10, 10000)

    def get_company_industry(self, company_name: str) -> str:
        # In a real scenario, you would use an API or database to get this information
        # For this example, we'll return a random industry
        import random
        industries = ['Technology', 'Finance', 'Healthcare', 'Education', 'Retail']
        return random.choice(industries)

    def send_email(self, to_email: str, name: str, template_name: str) -> bool:
        try:
            template = self.email_templates.get(template_name)
            if not template:
                logging.error(f"Email template {template_name} not found")
                return False

            msg = MIMEMultipart()
            msg['From'] = self.config['email_sender']
            msg['To'] = to_email
            msg['Subject'] = "Regarding our services"

            body = template.format(name=name)
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
            server.starttls()
            server.login(self.config['email_username'], self.config['email_password'])
            server.send_message(msg)
            server.quit()

            logging.info(f"Email sent to {to_email}")
            return True
        except Exception as e:
            logging.error(f"Error sending email: {str(e)}")
            return False

    def send_sms(self, lead_id: str, message: str) -> bool:
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
            lead = cursor.fetchone()
            
            if not lead:
                logging.error(f"Lead {lead_id} not found")
                return False

            # Assuming the phone number is stored in the database
            # You might need to adjust this based on your database schema
            phone_number = lead[5]  # Adjust the index as needed

            message = self.twilio_client.messages.create(
                body=message,
                from_=self.config['twilio_phone_number'],
                to=phone_number
            )
            logging.info(f"SMS sent to lead {lead_id}: {message.sid}")
            return True
        except Exception as e:
            logging.error(f"Failed to send SMS to lead {lead_id}: {str(e)}")
            return False

    def generate_detailed_report(self) -> Dict:
        try:
            cursor = self.db_conn.cursor()
            
            # Get basic stats
            cursor.execute("SELECT COUNT(*) FROM leads")
            total_leads = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM contact_attempts")
            total_contacts = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM leads WHERE qualification = 'Priority Lead'")
            qualified_leads = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM leads WHERE qualification = 'Disqualified'")
            disqualified_leads = cursor.fetchone()[0]
            
            # Get lead scores distribution
            cursor.execute("SELECT score FROM leads WHERE score IS NOT NULL")
            scores = [row[0] for row in cursor.fetchall()]
            score_distribution = {
                'min': min(scores) if scores else 0,
                'max': max(scores) if scores else 0,
                'average': sum(scores) / len(scores) if scores else 0
            }
            
            # Get qualification distribution
            cursor.execute("SELECT qualification, COUNT(*) FROM leads GROUP BY qualification")
            qualification_distribution = dict(cursor.fetchall())
            
            # Get contact attempt success rate
            cursor.execute("SELECT COUNT(*) FROM contact_attempts WHERE result = 'success'")
            successful_attempts = cursor.fetchone()[0]
            success_rate = successful_attempts / total_contacts if total_contacts > 0 else 0
            
            return {
                'total_leads': total_leads,
                'total_contacts': total_contacts,
                'qualified_leads': qualified_leads,
                'disqualified_leads': disqualified_leads,
                'score_distribution': score_distribution,
                'qualification_distribution': qualification_distribution,
                'contact_success_rate': success_rate
            }
        except Exception as e:
            logging.error(f"Error generating report: {str(e)}")
            return {}

    def visualize_report(self, report: Dict):
        try:
            # Pie chart for qualification distribution
            plt.figure(figsize=(10, 5))
            plt.pie(report['qualification_distribution'].values(), labels=report['qualification_distribution'].keys(), autopct='%1.1f%%')
            plt.title('Lead Qualification Distribution')
            plt.savefig('qualification_distribution.png')
            plt.close()

            # Bar chart for score distribution
            plt.figure(figsize=(10, 5))
            plt.bar(['Min Score', 'Max Score', 'Average Score'], [report['score_distribution']['min'], report['score_distribution']['max'], report['score_distribution']['average']])
            plt.title('Lead Score Distribution')
            plt.savefig('score_distribution.png')
            plt.close()

            logging.info("Report visualizations saved as PNG files.")
        except Exception as e:
            logging.error(f"Error visualizing report: {str(e)}")

    def __del__(self):
        if hasattr(self, 'db_conn'):
            self.db_conn.close()

# CLI interface
def cli():
    agent = LeadGenerationAgent()
    while True:
        print("\n1. Generate Lead")
        print("2. Qualify Lead")
        print("3. Send Outbound Contact")
        print("4. Process EOI")
        print("5. Transfer Lead")
        print("6. Generate Report")
        print("7. Exit")
        
        choice = input("Enter your choice: ")
        
        if choice == '1':
            name = input("Enter lead name: ")
            email = input("Enter lead email: ")
            company = input("Enter lead company: ")
            lead_id = agent.generate_lead({"name": name, "email": email, "company": company})
            print(f"Lead generated with ID: {lead_id}")
        elif choice == '2':
            lead_id = input("Enter lead ID: ")
            budget = input("Has budget? (y/n): ").lower() == 'y'
            authority = input("Has authority? (y/n): ").lower() == 'y'
            need = input("Has need? (y/n): ").lower() == 'y'
            timeline = input("Has timeline? (y/n): ").lower() == 'y'
            qualification = agent.qualify_lead(lead_id, {"budget": budget, "authority": authority, "need": need, "timeline": timeline})
            print(f"Lead qualified as: {qualification}")
        elif choice == '3':
            lead_id = input("Enter lead ID: ")
            channel = input("Enter channel (email/sms): ")
            success = agent.outbound_contact(lead_id, channel)
            print("Contact successful" if success else "Contact failed")
        elif choice == '4':
            lead_id = input("Enter lead ID: ")
            product_interest = input("Enter product interest: ")
            budget_range = input("Enter budget range: ")
            success = agent.process_eoi(lead_id, {"product_interest": product_interest, "budget_range": budget_range})
            print("EOI processed successfully" if success else "EOI processing failed")
        elif choice == '5':
            lead_id = input("Enter lead ID: ")
            sales_team_available = input("Is sales team available? (y/n): ").lower() == 'y'
            status = agent.transfer_lead(lead_id, sales_team_available)
            print(f"Transfer status: {status}")
        elif choice == '6':
            report = agent.generate_detailed_report()
            print(json.dumps(report, indent=2))
            agent.visualize_report(report)
            print("Report visualizations saved as PNG files.")
        elif choice == '7':
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    cli()