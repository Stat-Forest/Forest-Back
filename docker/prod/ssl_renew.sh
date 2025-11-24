# 📅 log for date
echo "[$(date)] SSL renew started"

# ✅ Certbot update
docker-compose -f /root/Forest-Back/docker/prod/docker-compose-prod.yml run --rm forest_certbot renew

# 🔁 NGINX reload
docker-compose -f /root/Forest-Back/docker/prod/docker-compose-prod.yml exec forest_nginx nginx -s reload

echo "[$(date)] SSL renew completed"
