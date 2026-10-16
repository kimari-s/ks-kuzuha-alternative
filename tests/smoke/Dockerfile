# Shared-host stand-in: PHP 7.4 (the minimum supported) + Apache with
# mod_rewrite and .htaccess honoured. The site is mounted at /var/www/html.
FROM php:7.4-apache
RUN a2enmod rewrite \
 && sed -i 's/AllowOverride None/AllowOverride All/' /etc/apache2/apache2.conf
