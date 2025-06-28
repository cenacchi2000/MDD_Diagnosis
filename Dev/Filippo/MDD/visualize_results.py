import os
import sys

# Ensure local imports work when run directly
sys.path.append(os.path.dirname(__file__))


from web_dashboard import run

if __name__ == "__main__":
    run()

