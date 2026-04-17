FROM python:3.9-slim-bullseye

# Install system-level dependencies required by Odoo 15
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
      git ca-certificates \
      libxml2-dev libxslt1-dev libldap2-dev libsasl2-dev \
      libtiff5-dev libjpeg8-dev libopenjp2-7-dev zlib1g-dev \
      libfreetype6-dev liblcms2-dev libwebp-dev libharfbuzz-dev \
      libfribidi-dev libxcb1-dev libpq-dev \
      postgresql-client \
      node-less npm \
    && rm -rf /var/lib/apt/lists/*

# Clone Odoo 15 source (shallow to keep image lean)
RUN git clone --depth=1 --branch=15.0 \
      https://github.com/odoo/odoo.git /opt/odoo

# Install Odoo Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /opt/odoo/requirements.txt \
    && pip install --no-cache-dir -e /opt/odoo

WORKDIR /workspace
