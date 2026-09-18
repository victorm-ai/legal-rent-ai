#!/bin/sh
set -eu

export API_BACKEND_URL="${API_BACKEND_URL:-http://api:8000}"
API_BACKEND_HOST="${API_BACKEND_HOST:-}"
if [ -z "$API_BACKEND_HOST" ]; then
  API_BACKEND_HOST="$(echo "$API_BACKEND_URL" | sed -e 's|^https\?://||' -e 's|/.*||')"
fi
export API_BACKEND_HOST

envsubst '${API_BACKEND_URL} ${API_BACKEND_HOST}' < /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf

exec nginx -g 'daemon off;'
