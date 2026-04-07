#!/bin/bash

cd /Users/whizmindsacademy/quant_lab

cp storage/*.csv reporting/

git add .
git commit -m "AUTO LOG $(date +%Y-%m-%d)"
git push

