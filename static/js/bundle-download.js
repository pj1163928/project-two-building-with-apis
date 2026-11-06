// "Download bundle" (catalog/partials/entry_files.html): the files the member's
// download defaults pick, fetched by the browser straight from the provider and
// saved as one zip, with a CREDITS.txt holding the license and attribution.
// The Toolbox never downloads, hosts or proxies the files (PRD, Out of Scope):
// the page only carries their URLs (json_script "entry-bundle-data").
//
// One file is saved as it is. Several are packed into a "stored" zip (no
// compression: the maps and models are compressed already) written by the
// small ZIP writer below. A file the provider won't hand over (a network error,
// or a host that refuses cross-origin reads) is listed in MISSING.txt instead,
// so the rest still arrive; if none arrive, the member is told to use the links.
(function () {
  // ---------- ZIP (stored, with CRC-32) ----------
  var CRC_TABLE = (function () {
    var table = new Uint32Array(256);
    for (var n = 0; n < 256; n += 1) {
      var c = n;
      for (var k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
      table[n] = c >>> 0;
    }
    return table;
  })();

  function crc32(bytes) {
    var crc = 0xffffffff;
    for (var i = 0; i < bytes.length; i += 1) crc = CRC_TABLE[(crc ^ bytes[i]) & 0xff] ^ (crc >>> 8);
    return (crc ^ 0xffffffff) >>> 0;
  }

  function dosDateTime(date) {
    var time = (date.getHours() << 11) | (date.getMinutes() << 5) | Math.floor(date.getSeconds() / 2);
    var day = ((date.getFullYear() - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate();
    return { time: time, date: day };
  }

  // entries: [{path, bytes (Uint8Array)}] -> Blob of a zip archive.
  function buildZip(entries) {
    var encoder = new TextEncoder();
    var stamp = dosDateTime(new Date());
    var parts = [];
    var central = [];
    var offset = 0;
    entries.forEach(function (entry) {
      var name = encoder.encode(entry.path);
      var crc = crc32(entry.bytes);
      var size = entry.bytes.length;
      var local = new DataView(new ArrayBuffer(30));
      local.setUint32(0, 0x04034b50, true);
      local.setUint16(4, 20, true); // version needed
      local.setUint16(6, 0x0800, true); // UTF-8 names
      local.setUint16(8, 0, true); // stored
      local.setUint16(10, stamp.time, true);
      local.setUint16(12, stamp.date, true);
      local.setUint32(14, crc, true);
      local.setUint32(18, size, true);
      local.setUint32(22, size, true);
      local.setUint16(26, name.length, true);
      local.setUint16(28, 0, true);
      parts.push(local.buffer, name, entry.bytes);

      var record = new DataView(new ArrayBuffer(46));
      record.setUint32(0, 0x02014b50, true);
      record.setUint16(4, 20, true); // made by
      record.setUint16(6, 20, true); // needed
      record.setUint16(8, 0x0800, true);
      record.setUint16(10, 0, true);
      record.setUint16(12, stamp.time, true);
      record.setUint16(14, stamp.date, true);
      record.setUint32(16, crc, true);
      record.setUint32(20, size, true);
      record.setUint32(24, size, true);
      record.setUint16(28, name.length, true);
      record.setUint32(42, offset, true); // the rest (extra, comment, disk, attributes) is 0
      central.push(record.buffer, name);
      offset += 30 + name.length + size;
    });
    var centralSize = central.reduce(function (total, part) { return total + part.byteLength; }, 0);
    var end = new DataView(new ArrayBuffer(22));
    end.setUint32(0, 0x06054b50, true);
    end.setUint16(8, entries.length, true);
    end.setUint16(10, entries.length, true);
    end.setUint32(12, centralSize, true);
    end.setUint32(16, offset, true);
    return new Blob(parts.concat(central, [end.buffer]), { type: "application/zip" });
  }

  // ---------- fetching ----------
  // The provider's file as bytes, reporting progress as it arrives.
  function fetchBytes(url, onBytes) {
    return fetch(url, { mode: "cors", credentials: "omit", referrerPolicy: "no-referrer" }).then(function (response) {
      if (!response.ok) throw new Error("HTTP " + response.status);
      if (!response.body || !response.body.getReader) {
        return response.arrayBuffer().then(function (buffer) { onBytes(buffer.byteLength); return new Uint8Array(buffer); });
      }
      var reader = response.body.getReader();
      var chunks = [];
      var length = 0;
      function read() {
        return reader.read().then(function (step) {
          if (step.done) {
            var bytes = new Uint8Array(length);
            var at = 0;
            chunks.forEach(function (chunk) { bytes.set(chunk, at); at += chunk.length; });
            return bytes;
          }
          chunks.push(step.value);
          length += step.value.length;
          onBytes(step.value.length);
          return read();
        });
      }
      return read();
    });
  }

  function save(blob, name) {
    var link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(function () { URL.revokeObjectURL(link.href); }, 60000);
  }

  function baseName(path) { return path.split("/").pop(); }

  // ---------- the button ----------
  function setState(box, state, message, progress) {
    box.dataset.bundleState = state;
    var status = box.querySelector("[data-bundle-status]");
    if (status) status.textContent = message || "";
    var bar = box.querySelector("[data-bundle-progress]");
    if (bar) bar.style.setProperty("--progress", progress == null ? 0 : progress);
  }

  function download(button) {
    var box = button.closest("#entry-bundle") || button.parentElement;
    var data = document.getElementById(button.dataset.bundleDownload);
    if (!data || box.dataset.bundleState === "working") return;
    var bundle = JSON.parse(data.textContent);
    var files = bundle.files;
    var expected = files.reduce(function (total, file) { return total + (file.size || 0); }, 0);
    var received = 0;
    var done = 0;
    var missing = [];
    var entries = [];
    button.disabled = true;
    setState(box, "working", "Fetching 1 of " + files.length + " from " + bundle.provider + "…", 0);

    function onBytes(count) {
      received += count;
      if (expected) setState(box, "working", box.querySelector("[data-bundle-status]").textContent, Math.min(1, received / expected));
    }

    // One at a time, so a big bundle never holds several downloads open at once.
    var chain = Promise.resolve();
    files.forEach(function (file, index) {
      chain = chain.then(function () {
        setState(box, "working", "Fetching " + (index + 1) + " of " + files.length + " from " + bundle.provider + "…", expected ? received / expected : index / files.length);
        return fetchBytes(file.url, onBytes).then(function (bytes) {
          entries.push({ path: file.path, bytes: bytes });
          done += 1;
        }, function () {
          missing.push(file);
        });
      });
    });

    chain.then(function () {
      if (!entries.length) {
        setState(box, "error", bundle.provider + " didn't hand the files over to this page. Use the file links below instead.", 0);
        return;
      }
      if (files.length === 1) {
        save(new Blob([entries[0].bytes]), baseName(entries[0].path));
      } else {
        var encoder = new TextEncoder();
        var folder = files[0].path.split("/")[0];
        entries.push({ path: folder + "/CREDITS.txt", bytes: encoder.encode(bundle.credits) });
        if (missing.length) {
          var lines = ["These files couldn't be fetched from " + bundle.provider + ". Download them from their links:", ""];
          missing.forEach(function (file) { lines.push(file.path + "  " + file.url); });
          entries.push({ path: folder + "/MISSING.txt", bytes: encoder.encode(lines.join("\n") + "\n") });
        }
        save(buildZip(entries), bundle.zip_name);
      }
      var note = missing.length ? done + " of " + files.length + " files saved; MISSING.txt lists the rest." : "Saved " + (files.length === 1 ? baseName(files[0].path) : bundle.zip_name) + ".";
      setState(box, missing.length ? "error" : "done", note, 1);
    }).catch(function () {
      setState(box, "error", "The bundle couldn't be built. Use the file links below instead.", 0);
    }).then(function () {
      button.disabled = false;
    });
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest && event.target.closest("[data-bundle-download]");
    if (button) download(button);
  });

  // For the tests in the browser: the zip writer on its own.
  window.axcenityZip = { build: buildZip, crc32: crc32 };
})();
