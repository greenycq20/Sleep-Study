# Sleep as Android Webhook (Preview)

The **Sleep as Android Webhook** connector logs real-time snoring, coughing, and stability audio events tracked by the popular Sleep as Android automation suite.

---

## Webhook Ingestion Configuration

To route webhooks from Sleep as Android to your self-hosted dashboard:

1. Open **Sleep as Android** on your phone.
2. Navigate to **Settings** → **Services** → **Automation** → **Webhooks**.
3. Enable **Webhooks**.
4. Paste your dashboard's webhook URL inside the endpoint input field:
   `http://your-server-ip:8000/api/connectors/sleep_as_android/import`
5. Test the connection. During sleep tracking, the app will automatically push event timestamps and occurrences (such as snoring or coughing counts) directly to your server.
