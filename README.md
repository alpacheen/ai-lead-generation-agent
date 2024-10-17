# AI Lead Generation Agent

An advanced AI-powered lead generation system designed to streamline the process of identifying, qualifying, and managing potential business opportunities.

## Features

- Automated lead generation and qualification
- Multi-channel communication (email, SMS)
- Advanced lead scoring algorithm
- CRM integration
- Detailed reporting and analytics
- Visualization of lead data
- CLI interface for easy interaction
- Comprehensive unit testing

## Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/ai-lead-generation-agent.git
   cd ai-lead-generation-agent
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure the application:
   - Copy `config.json.example` to `config.json`
   - Edit `config.json` with your specific settings (database, email, Twilio, CRM API)

4. Initialize the database:
   ```
   python lead_generation_agent.py --init-db
   ```

5. Run the application:
   ```
   python lead_generation_agent.py
   ```

## Usage

The application provides a CLI interface with the following options:

1. Generate Lead
2. Qualify Lead
3. Send Outbound Contact
4. Process EOI (Expression of Interest)
5. Transfer Lead
6. Generate Report
7. Exit

Follow the prompts to interact with the system.

## Testing

Run the unit tests:

```
python -m unittest test_lead_generation_agent.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.