# 📅 log for date
echo "[$(date)] SSL renew started"

# ✅ Certbot update
docker-compose run --rm forest_certbot renew

# 🔁 NGINX reload
docker-compose exec forest_nginx nginx -s reload

echo "[$(date)] SSL renew completed"
