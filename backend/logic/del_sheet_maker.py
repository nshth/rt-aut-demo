import os
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials as UserCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from backend.db.schema import InvoiceToolRequest

# load env
load_dotenv(dotenv_path="C:/Users/Rasha/Desktop/rt-aut-demo/.env")

# Scopes required
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets"
]

CLIENT_SECRETS_FILE = os.getenv("GOOGLE_OAUTH_CLIENT_SECRETS", "client_secrets.json")
TOKEN_PATH = os.getenv("TOKEN_PATH", "token.json")
PARENT_FOLDER_ID = os.getenv("DELIVERY_SHEET_FOLDER_ID")  # must be set

if not PARENT_FOLDER_ID:
    raise ValueError("DELIVERY_SHEET_FOLDER_ID not found in .env")

def get_user_credentials():
    # why token?
    creds = None
    if os.path.exists(TOKEN_PATH):
        try:
            creds = UserCredentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        except Exception:
            creds = None
    # why refresh? what happens if need refresh?
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save token for later use
        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())
    return creds

# is this error handling?
def debug_print_http_error(e: HttpError):
    print("HttpError status:", getattr(e.resp, "status", None))
    try:
        print("HttpError content:", e.content.decode() if isinstance(e.content, bytes) else e.content)
    except Exception:
        print("HttpError content (raw):", e.content)


def make_delivery_sheet(data: InvoiceToolRequest):
    creds = get_user_credentials()
    sheets_service = build("sheets", "v4", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)

    month_name = datetime.now().strftime("%B")
    sheet_title = datetime.now().strftime("%d/%m/%Y")
    spreadsheet_name = f"Delivery-Sheet-{month_name}"

    # 1. Find monthly spreadsheet (owned by you) inside parent folder
    query = f"name='{spreadsheet_name}' and mimeType='application/vnd.google-apps.spreadsheet' and '{PARENT_FOLDER_ID}' in parents and trashed=false"
    try:
        q_resp = drive_service.files().list(q=query, spaces="drive", fields="files(id,name,owners)").execute()
    except HttpError as e:
        debug_print_http_error(e)
        raise

    files = q_resp.get("files", [])
    if files:
        spreadsheet_id = files[0]["id"]
        owner_info = files[0].get("owners", [])
        print(f"Found spreadsheet: {spreadsheet_name}, id={spreadsheet_id}, owners={owner_info}")
    else:
        spreadsheet_body = {
            "properties": {"title": spreadsheet_name},
            "sheets": [{"properties": {"title": sheet_title}}]
        }
        try:
            print("Creating spreadsheet via Sheets API...")
            spreadsheet = sheets_service.spreadsheets().create(body=spreadsheet_body).execute()
            spreadsheet_id = spreadsheet.get("spreadsheetId")
            print("Created spreadsheet id:", spreadsheet_id)

            try:
                drive_service.files().update(
                    fileId=spreadsheet_id,
                    addParents=PARENT_FOLDER_ID,
                    removeParents="root",
                    fields="id, parents"
                ).execute()
                print("Moved spreadsheet into parent folder.")
            except HttpError as e:
                print("Failed to move spreadsheet into parent folder (not fatal).")
                debug_print_http_error(e)
        except HttpError as e:
            print("Failed to create spreadsheet.")
            debug_print_http_error(e)
            raise

    try:
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    except HttpError as e:
        print("Failed to fetch spreadsheet metadata.")
        debug_print_http_error(e)
        raise

    sheet_exists = any(s["properties"]["title"] == sheet_title for s in spreadsheet.get("sheets", []))
    if not sheet_exists:
        print(f"Adding new sheet/tab: {sheet_title}")
        try:
            add_sheet_request = {"addSheet": {"properties": {"title": sheet_title}}}
            response = sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": [add_sheet_request]}
            ).execute()
            new_sheet_id = response["replies"][0]["addSheet"]["properties"]["sheetId"]

            requests = [{
                "repeatCell": {
                    "range": {"sheetId": new_sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {"bold": True},
                            "horizontalAlignment": "CENTER"
                        }
                    },
                    "fields": "userEnteredFormat(textFormat,horizontalAlignment)"
                }
            }]

            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body={"requests": requests}
            ).execute()

        except HttpError as e:
            print("Failed to create new sheet/tab.")
            debug_print_http_error(e)
            raise

    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_title}'!A1:F1"
    ).execute()
    first_row = result.get("values", [])

    if not first_row:
        headers = [["Customer Name", "Contact", "Address", "Product", "Quantity", "Total Price"]]
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_title}'!A1:F1",
            valueInputOption="USER_ENTERED",
            body={"values": headers}
        ).execute()
        print("Headers added.")

    # 4. Append invoice data
    try:
        result = sheets_service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=f"'{sheet_title}'!A:A").execute()
        current_rows = len(result.get("values", []))
        next_row = current_rows + 1 if current_rows > 0 else 2
        values = [[
            data.customer_name,
            data.customer_contact,
            data.customer_address,
            data.product_name,
            data.quantity_needed,
            data.total_price
        ]]
        sheets_service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_title}'!A{next_row}:F{next_row}",
            valueInputOption="USER_ENTERED",
            body={"values": values}
        ).execute()

        # Fetch sheetId dynamically
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = {s["properties"]["title"]: s["properties"]["sheetId"] for s in spreadsheet.get("sheets", [])}
        sheet_id = sheets[sheet_title]

        # Center all data rows including the new one
        requests = [{
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,              
                    "endRowIndex": next_row,         
                    "startColumnIndex": 0,
                    "endColumnIndex": 6
                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat.horizontalAlignment"
            }
        }]

        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests}
        ).execute()

        
        print(f"Appended data to {spreadsheet_name}/{sheet_title}")
    except HttpError as e:
        print("Failed to append row.")
        debug_print_http_error(e)
        raise

    return f"Data written to: Parent Folder/{spreadsheet_name}/{sheet_title}"


if __name__ == "__main__":
    demo_order = InvoiceToolRequest(
        customer_name="John Doe",
        customer_contact="0712345678",
        customer_address="123 Demo Street, Colombo",
        product_name="Gaming Chair",
        quantity_needed=2,
        total_price=50000.0
    )
    print(make_delivery_sheet(demo_order))
