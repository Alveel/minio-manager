from dotenv import find_dotenv, load_dotenv

# Load environment variables from .env file from the current working directory.
dotenv_path = find_dotenv(filename="config.env", usecwd=True)
load_dotenv(dotenv_path, override=True, verbose=True)
