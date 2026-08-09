# Python 3.10 has better pre-compiled wheels for heavy libraries like CadQuery & SciPy
FROM python:3.10-slim

# Install system dependencies required for WeasyPrint and CAD processing
RUN apt-get update && apt-get install -y \
    build-essential \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libffi-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    mesa-utils \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Upgrade PIP and install 'wheel' FIRST to prevent build compilation errors
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Now install the heavy requirements (This will be much faster and safer now)
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]