// Refuse to deploy without a wrangler.toml or with the example values of
// wrangler.example.toml still in it.
const fs = require('fs');
const path = require('path');

const file = path.join(__dirname, '..', 'wrangler.toml');
if (!fs.existsSync(file)) {
  console.error('wrangler.toml not found: cp wrangler.example.toml wrangler.toml, then edit it');
  process.exit(1);
}
const config = fs.readFileSync(file, 'utf8');
const left = ['example.com', 'your-bucket'].filter((value) => config.includes(value));
if (left.length) {
  console.error(`wrangler.toml still has example values: ${left.join(', ')}`);
  process.exit(1);
}
