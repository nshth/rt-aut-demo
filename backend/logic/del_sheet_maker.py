import os
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials as UserCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from backend.db.schema import InvoiceToolRequest

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets"
]

CLIENT_SECRETS_FILE = os.getenv("GOOGLE_OAUTH_CLIENT_SECRETS", "client_secrets.json")
TOKEN_PATH = os.getenv("TOKEN_PATH", "token.json")
PARENT_FOLDER_ID = os.getenv("DELIVERY_SHEET_FOLDER_ID")  # must be set

if not PARENT_FOLDER_ID:
    raise ValueError("DELIVERY_SHEET_FOLDER_ID not found in environment variables")

def get_user_credentials():
    """
    Return valid user credentials.
    - TOKEN_PATH stores the user's OAuth tokens so they don't re-auth every time.
    - If the token is expired and a refresh_token is present, we refresh it.
    - Otherwise we start a local server flow to get new credentials.
    """
    creds = None
    if os.path.exists(TOKEN_PATH):
        try:
            creds = UserCredentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # persist token for next runs
        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())
    return creds

def debug_print_http_error(e: HttpError):
    print("HttpError status:", getattr(e.resp, "status", None))
    try:
        print("HttpError content:", e.content.decode() if isinstance(e.content, bytes) else e.content)
    except Exception:
        print("HttpError content (raw):", e.content)

def make_delivery_sheet(data: InvoiceToolRequest) -> str:
    """
    Appends one delivery row to the monthly delivery sheet inside PARENT_FOLDER_ID.
    Returns a string path for debug/confirmation.
    """
    creds = get_user_credentials()
    sheets_service = build("sheets", "v4", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)

    month_name = datetime.now().strftime("%B")
    sheet_title = datetime.now().strftime("%d-%m-%Y")
    spreadsheet_name = f"Delivery-Sheet-{month_name}"

    # Find spreadsheet in the parent folder
    query = (
        f"name='{spreadsheet_name}' and mimeType='application/vnd.google-apps.spreadsheet' "
        f"and '{PARENT_FOLDER_ID}' in parents and trashed=false"
    )
    try:
        q_resp = drive_service.files().list(q=query, spaces="drive", fields="files(id,name,owners)").execute()
    except HttpError as e:
        debug_print_http_error(e)
        raise

    files = q_resp.get("files", [])
    if files:
        spreadsheet_id = files[0]["id"]
    else:
        # Create a monthly spreadsheet and move it to parent folder
        spreadsheet_body = {
            "properties": {"title": spreadsheet_name},
            "sheets": [{"properties": {"title": sheet_title}}]
        }
        try:
            spreadsheet = sheets_service.spreadsheets().create(body=spreadsheet_body).execute()
            spreadsheet_id = spreadsheet.get("spreadsheetId")
            try:
                drive_service.files().update(
                    fileId=spreadsheet_id,
                    addParents=PARENT_FOLDER_ID,
                    removeParents="root",
                    fields="id, parents"
                ).execute()
            except HttpError as e:
                # Not fatal, just warn
                debug_print_http_error(e)
        except HttpError as e:
            debug_print_http_error(e)
            raise

    # Ensure header row exists in today's sheet/tab
    try:
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    except HttpError as e:
        debug_print_http_error(e)
        raise

    sheet_exists = any(s["properties"]["title"] == sheet_title for s in spreadsheet.get("sheets", []))
    if not sheet_exists:
        try:
            add_sheet_request = {"addSheet": {"properties": {"title": sheet_title}}}
            response = sheets_service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id,
                                                                body={"requests": [add_sheet_request]}).execute()
            new_sheet_id = response["replies"][0]["addSheet"]["properties"]["sheetId"]
            #style header
            headers = [["Customer Name", "Contact", "Address", "Product", "Quantity", "Total Price"]]
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_title}'!A1:F1",
                valueInputOption="USER_ENTERED",
                body={"values": headers}
            ).execute()
        except HttpError as e:
            debug_print_http_error(e)
            raise

    # Append the invoice row
    try:
        # find next row index
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
    except HttpError as e:
        debug_print_http_error(e)
        raise

    return f"Appended to: {spreadsheet_name}/{sheet_title}"

creds = get_user_credentials()
