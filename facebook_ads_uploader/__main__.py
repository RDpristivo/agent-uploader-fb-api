from facebook_ads_uploader.main import run

# Add a handler to provide better error messages on common errors
if __name__ == "__main__":
    import sys

    try:
        run()
    except Exception as e:
        if "tab not found" in str(e).lower() or "worksheet not found" in str(e).lower():
            print("\nERROR: Specified tab not found in spreadsheet.")
            print("Try running with --list-tabs to see available tabs")
        else:
            print(f"\nERROR: {e}")

        if "--debug" in sys.argv:
            import traceback

            traceback.print_exc()
        sys.exit(1)
