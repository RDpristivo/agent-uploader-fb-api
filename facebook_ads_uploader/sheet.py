import gspread
import logging
from typing import List, Tuple, Dict, Any, Optional
from time import sleep

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_rows_to_upload(credentials_file: str, spreadsheet_id: str, tab_name: str):
    """
    Connect to Google Sheets using a service account and retrieve all rows from the specified tab.
    Returns a tuple: (worksheet, list_of_rows), where list_of_rows contains (row_index, row_data_dict)
    for all rows.

    The main.py file will handle filtering based on 'Upload' and 'Platform' values.
    """
    if not credentials_file:
        raise ValueError("Credentials file path is required")
    if not spreadsheet_id:
        raise ValueError("Spreadsheet ID is required")
    if not tab_name:
        raise ValueError("Tab name is required")

    # Authenticate and open the spreadsheet with retries
    max_retries = 3
    retry_count = 0
    last_error = None

    while retry_count < max_retries:
        try:
            # Authenticate and open the spreadsheet
            gc = gspread.service_account(filename=credentials_file)
            sh = gc.open_by_key(spreadsheet_id)
            try:
                worksheet = sh.worksheet(tab_name)
                logger.info(f"Successfully opened worksheet '{tab_name}'")
                break  # Break the retry loop if successful
            except Exception as e:
                last_error = e
                logger.error(f"Could not open tab '{tab_name}': {e}")
                # Try again with forward slash conversion (in case of date format issue)
                try:
                    alt_tab_name = tab_name.replace("/", "-")
                    worksheet = sh.worksheet(alt_tab_name)
                    logger.info(
                        f"Opened worksheet using alternative name '{alt_tab_name}'"
                    )
                    break  # Break the retry loop if successful
                except Exception:
                    logger.error(
                        f"Could not open tab with alternative name '{alt_tab_name}' either"
                    )
                    raise RuntimeError(f"Could not open tab '{tab_name}': {e}")
        except Exception as e:
            last_error = e
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(
                    f"Attempt {retry_count} failed. Retrying in 2 seconds... Error: {e}"
                )
                sleep(2)  # Wait before retrying
            else:
                logger.error(
                    f"All {max_retries} attempts to connect to Google Sheets failed"
                )
                raise RuntimeError(
                    f"Failed to connect to Google Sheets after {max_retries} attempts: {e}"
                )

    if not worksheet:
        raise RuntimeError(f"Could not open worksheet: {last_error}")

    # Fetch all records from the sheet
    try:
        records = worksheet.get_all_records()
        logger.info(f"Retrieved {len(records)} records from worksheet")
    except Exception as e:
        logger.error(f"Failed to get records from worksheet: {e}")
        raise RuntimeError(f"Failed to get records from worksheet: {e}")

    rows_to_process = []

    # Get all rows, including the special ad category and device targeting columns
    # The decision to filter will be handled in main.py
    for idx, record in enumerate(
        records, start=2
    ):  # data starts at row 2 (row 1 is header)
        # Add the row to be processed
        rows_to_process.append((idx, record))

    return worksheet, rows_to_process


def ensure_status_columns(worksheet) -> Tuple[int, int]:
    """
    Ensure that 'Status' and 'Error' columns exist in the worksheet.
    If missing, append them to the header row. Returns (status_col_index, error_col_index).
    """
    try:
        header = worksheet.row_values(1)
        logger.debug(f"Header row: {header}")
        status_col_index = None
        error_col_index = None

        # Check for "Status" column (case-insensitive)
        status_col_names = ["Status", "status", "STATUS"]
        for col_name in status_col_names:
            if col_name in header:
                status_col_index = header.index(col_name) + 1  # convert to 1-indexed
                logger.debug(f"Found Status column at index {status_col_index}")
                break

        # Check for "Error" column (case-insensitive)
        error_col_names = ["Error", "error", "ERROR"]
        for col_name in error_col_names:
            if col_name in header:
                error_col_index = header.index(col_name) + 1  # convert to 1-indexed
                logger.debug(f"Found Error column at index {error_col_index}")
                break

        # Add Status column if not found
        if status_col_index is None:
            next_col = len(header) + 1
            try:
                # Try to add the Status column
                worksheet.update_cell(1, next_col, "Status")
                status_col_index = next_col
                header.append("Status")
                logger.info(f"Added Status column at index {status_col_index}")
            except Exception as e:
                if "exceeds grid limits" in str(e):
                    # Handle grid limits error by expanding the sheet first
                    try:
                        # Get the current number of columns in the sheet
                        properties = worksheet.spreadsheet.fetch_sheet_metadata().get(
                            "sheets", []
                        )
                        for sheet in properties:
                            if (
                                sheet.get("properties", {}).get("title")
                                == worksheet.title
                            ):
                                current_cols = (
                                    sheet.get("properties", {})
                                    .get("gridProperties", {})
                                    .get("columnCount", 0)
                                )
                                break
                        else:
                            current_cols = 0

                        # Expand the grid with enough columns
                        if current_cols > 0 and next_col > current_cols:
                            # Request to resize the sheet
                            worksheet.spreadsheet.batch_update(
                                {
                                    "requests": [
                                        {
                                            "updateSheetProperties": {
                                                "properties": {
                                                    "sheetId": worksheet.id,
                                                    "gridProperties": {
                                                        "columnCount": next_col
                                                        + 2  # Add 2 extra columns for safety
                                                    },
                                                },
                                                "fields": "gridProperties.columnCount",
                                            }
                                        }
                                    ]
                                }
                            )
                            logger.info(f"Expanded sheet to {next_col + 2} columns")

                            # Now try to add the Status column again
                            worksheet.update_cell(1, next_col, "Status")
                            status_col_index = next_col
                            header.append("Status")
                            logger.info(
                                f"Added Status column at index {status_col_index} after expanding sheet"
                            )
                    except Exception as expand_err:
                        logger.error(f"Failed to expand sheet: {expand_err}")
                        # Fallback to reuse an existing column if possible
                        if len(header) >= 2:
                            fallback_col = len(header)  # Use last column as fallback
                            worksheet.update_cell(1, fallback_col, "Status")
                            status_col_index = fallback_col
                            header[fallback_col - 1] = (
                                "Status"  # Update our local copy of header
                            )
                            logger.info(
                                f"Used column {fallback_col} for Status as fallback"
                            )
                        else:
                            # If all else fails, raise the exception
                            raise RuntimeError(f"Could not add Status column: {e}")
                else:
                    # For other types of errors, re-raise
                    raise RuntimeError(f"Could not add Status column: {e}")

        # Add Error column if not found
        if error_col_index is None:
            next_col = len(header) + 1
            try:
                # Try to add the Error column
                worksheet.update_cell(1, next_col, "Error")
                error_col_index = next_col
                header.append("Error")
                logger.info(f"Added Error column at index {error_col_index}")
            except Exception as e:
                if "exceeds grid limits" in str(e):
                    # Handle grid limits error by expanding the sheet first
                    try:
                        # Get the current number of columns in the sheet
                        properties = worksheet.spreadsheet.fetch_sheet_metadata().get(
                            "sheets", []
                        )
                        for sheet in properties:
                            if (
                                sheet.get("properties", {}).get("title")
                                == worksheet.title
                            ):
                                current_cols = (
                                    sheet.get("properties", {})
                                    .get("gridProperties", {})
                                    .get("columnCount", 0)
                                )
                                break
                        else:
                            current_cols = 0

                        # Expand the grid with enough columns
                        if current_cols > 0 and next_col > current_cols:
                            # Request to resize the sheet
                            worksheet.spreadsheet.batch_update(
                                {
                                    "requests": [
                                        {
                                            "updateSheetProperties": {
                                                "properties": {
                                                    "sheetId": worksheet.id,
                                                    "gridProperties": {
                                                        "columnCount": next_col
                                                        + 2  # Add 2 extra columns for safety
                                                    },
                                                },
                                                "fields": "gridProperties.columnCount",
                                            }
                                        }
                                    ]
                                }
                            )
                            logger.info(f"Expanded sheet to {next_col + 2} columns")

                            # Now try to add the Error column again
                            worksheet.update_cell(1, next_col, "Error")
                            error_col_index = next_col
                            header.append("Error")
                            logger.info(
                                f"Added Error column at index {error_col_index} after expanding sheet"
                            )
                    except Exception as expand_err:
                        logger.error(f"Failed to expand sheet: {expand_err}")
                        # Fallback to reuse an existing column if possible
                        if len(header) >= 1:
                            fallback_col = len(header)  # Use last column as fallback
                            worksheet.update_cell(1, fallback_col, "Error")
                            error_col_index = fallback_col
                            header[fallback_col - 1] = (
                                "Error"  # Update our local copy of header
                            )
                            logger.info(
                                f"Used column {fallback_col} for Error as fallback"
                            )
                        else:
                            # If all else fails, raise the exception
                            raise RuntimeError(f"Could not add Error column: {e}")
                else:
                    # For other types of errors, re-raise
                    raise RuntimeError(f"Could not add Error column: {e}")

        return status_col_index, error_col_index
    except Exception as e:
        logger.error(f"Error ensuring status columns: {e}")
        raise RuntimeError(f"Failed to ensure status columns: {e}")


def update_status_rows(
    worksheet, status_col: int, error_col: int, results: List[Tuple[int, str, str]]
):
    """
    Update the Status and Error columns for each row in results.
    `results` is a list of (row_index, status, error_message).

    Implements batch updates with retries for API reliability.
    """
    if not worksheet or not results:
        logger.warning("No worksheet or results provided for status update")
        return

    # Split updates into batches of 20 rows to avoid API limits
    batch_size = 20
    results_batches = [
        results[i : i + batch_size] for i in range(0, len(results), batch_size)
    ]
    logger.info(f"Updating {len(results)} rows in {len(results_batches)} batches")

    for batch_index, batch in enumerate(results_batches):
        cells_to_update = []
        for row_index, status, error in batch:
            if status is not None:
                cells_to_update.append(gspread.Cell(row_index, status_col, status))
            if error is not None:
                # Truncate very long error messages to avoid API issues
                if error and len(str(error)) > 1000:
                    error = str(error)[:997] + "..."
                cells_to_update.append(gspread.Cell(row_index, error_col, error))

        if cells_to_update:
            max_retries = 3
            retry_count = 0
            success = False

            while retry_count < max_retries and not success:
                try:
                    worksheet.update_cells(cells_to_update)
                    logger.info(
                        f"Successfully updated batch {batch_index+1}/{len(results_batches)} ({len(cells_to_update)} cells)"
                    )
                    success = True
                    # Add a small delay between batches to avoid rate limiting
                    if batch_index < len(results_batches) - 1:
                        sleep(1)
                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.warning(
                            f"Batch update attempt {retry_count} failed. Retrying in 2 seconds... Error: {e}"
                        )
                        sleep(2)  # Wait before retrying
                    else:
                        logger.error(
                            f"Failed to update status batch after {max_retries} attempts: {e}"
                        )
                        raise RuntimeError(f"Failed to update status batch: {e}")
