FROM python:3.8-slim-buster

# Create a new work-directory. Default location for all subsequent operations
WORKDIR /app

# Copy requirements.txt to workdir
COPY requirements.txt requirements.txt

# Install dependencies
RUN pip3 install -r requirements.txt

# Copy Source code to workdir
COPY . .

# Run the following command
CMD [ "python3", "-u", "shedder.py"]