import gspread


def get_rows_to_upload(credentials_file: str, spreadsheet_id: str, tab_name: str):
    """
    Connect to Google Sheets using a service account and retrieve all rows from the specified tab.
    Returns a tuple: (worksheet, list_of_rows), where list_of_rows contains (row_index, row_data_dict)
    for all rows.
    
    The main.py file will handle filtering based on 'Upload' and 'Platform' values.
    """
    # Authenticate and open the spreadsheet
    gc = gspread.service_account(filename=credentials_file)
    sh = gc.open_by_key(spreadsheet_id)
    try:
        worksheet = sh.worksheet(tab_name)
    except Exception as e:
        raise RuntimeError(f"Could not open tab '{tab_name}': {e}")
    
    # Fetch all records from the sheet
    records = worksheet.get_all_records()
    rows_to_process = []
    
    # Get all rows, including the special ad category and device targeting columns
    # The decision to filter will be handled in main.py
    for idx, record in enumerate(
        records, start=2
    ):  # data starts at row 2 (row 1 is header)
        # Add the row to be processed
        rows_to_process.append((idx, record))
        
    return worksheet, rows_to_process


def ensure_status_columns(worksheet):
    """
    Ensure that 'Status' and 'Error' columns exist in the worksheet.
    If missing, append them to the header row. Returns (status_col_index, error_col_index).
    """
    header = worksheet.row_values(1)
    status_col_index = None
    error_col_index = None
    # Check for "Status" column
    if "Status" in header:
        status_col_index = header.index("Status") + 1  # convert to 1-indexed
    else:
        next_col = len(header) + 1
        worksheet.update_cell(1, next_col, "Status")
        status_col_index = next_col
        header.append("Status")
    # Check for "Error" column
    if "Error" in header:
        error_col_index = header.index("Error") + 1
    else:
        next_col = len(header) + 1
        worksheet.update_cell(1, next_col, "Error")
        error_col_index = next_col
        header.append("Error")
    return status_col_index, error_col_index


def update_status_rows(worksheet, status_col, error_col, results):
    """
    Update the Status and Error columns for each row in results.
    `results` is a list of (row_index, status, error_message).
    """
    cells_to_update = []
    for row_index, status, error in results:
        if status is not None:
            cells_to_update.append(gspread.Cell(row_index, status_col, status))
        if error is not None:
            cells_to_update.append(gspread.Cell(row_index, error_col, error))
    if cells_to_update:
        worksheet.update_cells(cells_to_update)
