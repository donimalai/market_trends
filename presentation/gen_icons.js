const React = require('react');
const ReactDOMServer = require('react-dom/server');
const sharp = require('sharp');
const fs = require('fs');
const path = require('path');
const {
  FiTarget, FiDatabase, FiBarChart2, FiShield, FiCpu, FiUsers,
  FiArrowUpRight, FiCompass, FiFlag,
} = require('react-icons/fi');

const OUT = path.join(__dirname, 'assets');
if (!fs.existsSync(OUT)) fs.mkdirSync(OUT, { recursive: true });

const icons = {
  target: FiTarget,
  database: FiDatabase,
  chart: FiBarChart2,
  shield: FiShield,
  cpu: FiCpu,
  users: FiUsers,
  arrow: FiArrowUpRight,
  compass: FiCompass,
  flag: FiFlag,
};

async function run() {
  for (const [name, Icon] of Object.entries(icons)) {
    // react-icons already emits a self-contained <svg> with the correct
    // viewBox for its paths (0 0 24 24) plus width/height=256 -- wrapping
    // it in a second <svg viewBox="0 0 256 256"> (as an earlier version of
    // this script did) discards that viewBox and rescales the 24-unit
    // paths against a 256-unit box, shrinking the icon to a tiny fragment
    // in one corner. Use the library's own markup as-is.
    const svg = ReactDOMServer.renderToStaticMarkup(
      React.createElement(Icon, { size: 256, color: '#FFFFFF' })
    );
    await sharp(Buffer.from(svg)).png().toFile(path.join(OUT, `${name}.png`));
    console.log('wrote', name);
  }
}
run();
