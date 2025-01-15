/*****************************************************
 * A) Helper function to determine if an element is visible
 *****************************************************/
function isElementVisible(el) {
  if (!el || el.nodeType !== Node.ELEMENT_NODE) return false;

  const style = window.getComputedStyle(el);

  // Basic checks: display, visibility, opacity
  if (
    style.display === "none" ||
    style.visibility === "hidden" ||
    style.opacity === "0"
  ) {
    return false;
  }

  // Check dimensions
  if (el.offsetWidth <= 0 || el.offsetHeight <= 0) {
    return false;
  }

  return true;
}

/*****************************************************
 * B) Build a "signature" for an element, ignoring hidden children
 *****************************************************/
function buildSignature(el) {
  if (!el || !el.tagName) return "";

  const tagName = el.tagName.toLowerCase();

  // Gather and sort class names
  const classList = [...el.classList].sort().join(" ");

  // Gather immediate child *visible* tag names, one level deep
  const childTags = [];
  for (const child of el.children) {
    // Only include if the child is visible
    if (isElementVisible(child)) {
      childTags.push(child.tagName.toLowerCase());
    }
  }
  childTags.sort();
  const childTagsString = childTags.join("|");

  // Example: "div::person-card team-member::img|h3|p"
  return `${tagName}::${classList}::${childTagsString}`;
}

/*****************************************************
 * C) Count how many elements on the page share a given signature
 *****************************************************/
function countSignatureOccurrences(signature) {
  // Get all elements of the same tag type as signature's first token
  const [sigTag] = signature.split("::");
  const all = [...document.querySelectorAll(sigTag)];

  let count = 0;
  let maxTextLength = 0;

  for (const el of all) {
    // Also skip if this element is hidden
    if (!isElementVisible(el)) continue;

    const elSig = buildSignature(el);
    if (elSig === signature) {
      count++;
      const len = el.innerText.trim().length;
      if (len > maxTextLength) {
        maxTextLength = len;
      }
    }
  }

  return { count, maxTextLength };
}

/*****************************************************
 * D) Walk up the DOM from a matched element to find
 *    all "container" candidates
 *****************************************************/
function findContainerCandidates(startEl) {
  const containers = [];
  let current = startEl;

  while (current && current.nodeType === Node.ELEMENT_NODE) {
    const tagName = current.tagName.toLowerCase();
    // Only consider likely container tags
    if (/(div|li|section|article)/i.test(tagName)) {
      // Also skip if the container itself is hidden
      if (isElementVisible(current)) {
        containers.push(current);
      }
    }
    current = current.parentElement;
  }

  return containers;
}

/*****************************************************
 * E) Utility: Convert container's HTML into pretty text
 *    - Replaces <br>, <p>, <li>, <h1>-<h6>, etc.
 *    - Removes leftover tags
 *    - Creates spacing for readability
 *****************************************************/
function getReadableText(container) {
  // Clone the container to avoid modifying the DOM
  const clone = container.cloneNode(true);

  // Remove script and style tags to avoid clutter
  const scripts = clone.querySelectorAll("script, style");
  scripts.forEach((el) => el.remove());

  let html = clone.innerHTML;

  // 1) Convert <br> tags to newlines
  html = html.replace(/<br\s*\/?>/gi, "\n");
  // 2) Convert paragraph closing to double newline
  html = html.replace(/<\/p>/gi, "\n\n");
  // 3) Convert list items
  html = html.replace(/<li[^>]*>/gi, "• ");
  html = html.replace(/<\/li>/gi, "\n");
  // Extra line after a list is closed
  html = html.replace(/<\/ul>/gi, "\n");
  html = html.replace(/<\/ol>/gi, "\n");
  // 4) Convert headings
  html = html.replace(/<h[1-6][^>]*>/gi, "\n## ");
  html = html.replace(/<\/h[1-6]>/gi, "\n");

  // Remove all remaining HTML tags
  html = html.replace(/<[^>]+>/g, " ");

  // Normalize multiple newlines => double newlines
  html = html.replace(/\n\s*\n\s*\n+/g, "\n\n");

  // Remove trailing spaces on each line
  html = html.replace(/[ \t]+\n/g, "\n");

  // Trim leading/trailing whitespace
  html = html.trim();

  return html;
}

/*****************************************************
 * F) Utility: Extract all href links from a container
 *****************************************************/
function extractLinks(container) {
  const links = [];
  const anchorTags = container.querySelectorAll("a[href]");

  anchorTags.forEach((a) => {
    if (isElementVisible(a)) { // Ensure the link is visible
      const href = a.getAttribute("href").trim();
      const text = a.innerText.trim();
      // Only include if href is not empty
      if (href) {
        links.push({ text, href });
      }
    }
  });

  return links;
}

/*****************************************************
 * G) Utility: Trigger a text file download in-browser
 *****************************************************/
function downloadTextFile(text, fileName) {
  const blob = new Blob([text], { type: "text/plain" });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;

  // Programmatically click the link to trigger download
  document.body.appendChild(a);
  a.click();

  // Clean-up
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/*****************************************************
 * H) Main function to find the "best" person containers
 *****************************************************/
function findPersonContainers(knownName, topN = 5) {
  if (!knownName) {
    console.warn("Please provide a 'knownName' string.");
    return null;
  }

  // 1) Find all elements whose text includes knownName (case-sensitive here)
  const allElements = [...document.querySelectorAll("*")];
  const matchedElements = allElements.filter((el) => {
    // Skip hidden elements
    if (!isElementVisible(el)) return false;
    return el.textContent.includes(knownName);
  });

  if (!matchedElements.length) {
    console.warn(`No elements found containing "${knownName}".`);
    return null;
  }

  // 2) For each matched element, gather container candidates up the chain
  const signatureMap = new Map();
  // signatureMap maps signature -> { frequency, maxTextLen, exampleEl }

  for (const matchedEl of matchedElements) {
    const candidates = findContainerCandidates(matchedEl);

    for (const candidate of candidates) {
      const sig = buildSignature(candidate);

      // If not already calculated, count site-wide occurrences
      if (!signatureMap.has(sig)) {
        const { count, maxTextLength } = countSignatureOccurrences(sig);
        signatureMap.set(sig, {
          frequency: count,
          maxTextLen: maxTextLength,
          exampleEl: candidate,
        });
      }
    }
  }

  if (signatureMap.size === 0) {
    console.warn("No container candidates found up the DOM for knownName.");
    return null;
  }

  // 3) Sort signatures to find the "best" ones
  //    - Highest frequency
  //    - Tiebreak by largest text length
  const sortedSignatures = [...signatureMap.entries()].sort((a, b) => {
    const valA = a[1];
    const valB = b[1];
    // Primary: frequency
    if (valB.frequency !== valA.frequency) {
      return valB.frequency - valA.frequency;
    }
    // Tie-break: maxTextLen
    return valB.maxTextLen - valA.maxTextLen;
  });

  // Get top N signatures
  const topSignatures = sortedSignatures.slice(0, topN);

  if (!topSignatures.length) {
    console.warn("Could not find any suitable signatures after sorting.");
    return null;
  }

  // 4) For each top signature, gather all matching containers
  const topContainersList = topSignatures.map(([signature, data], idx) => {
    const [sigTag] = signature.split("::");
    const allOfBestTag = [...document.querySelectorAll(sigTag)];
    const bestContainers = allOfBestTag.filter((el) => {
      if (!isElementVisible(el)) return false;
      return buildSignature(el) === signature;
    });

    // Among these best containers, find the single largest (by text length)
    let largestContainer = null;
    let largestLen = 0;
    for (const bc of bestContainers) {
      const len = bc.innerText.trim().length;
      if (len > largestLen) {
        largestLen = len;
        largestContainer = bc;
      }
    }

    console.log(`Signature #${idx + 1}:`, signature);
    console.log(`Frequency: ${data.frequency}`);
    console.log(`Max text length: ${data.maxTextLen}`);
    console.log(`Number of matched containers: ${bestContainers.length}`);
    console.log(`Largest container text length: ${largestLen}`);

    return {
      signature,
      frequency: data.frequency,
      maxTextLength: data.maxTextLen,
      allContainers: bestContainers,
      largestContainer,
    };
  });

  return topContainersList;
}

// ... [previous helper functions A through H remain the same] ...

/*****************************************************
 * I) Main function to find and copy top person containers to clipboard
 *****************************************************/
function findAndCopyTopPersonContainers(knownName, topN = 5) {
  const topContainersList = findPersonContainers(knownName, topN);
  if (!topContainersList) {
    console.warn("No result found. Nothing to copy.");
    return;
  }

  // Prepare content for all top containers
  let finalText = "";

  topContainersList.forEach((containerData, idx) => {
    const { allContainers } = containerData;
    // For each container in this signature, extract and append text
    allContainers.forEach((container, cIdx) => {
      const readableText = getReadableText(container);
      const links = extractLinks(container);
      let containerText = `=== CONTAINER #${idx + 1} - Instance #${cIdx + 1} ===\n${readableText}\n`;

      if (links.length > 0) {
        containerText += `\nLinks:\n`;
        links.forEach((link, linkIdx) => {
          containerText += `- ${link.text || "Link " + (linkIdx + 1)}: ${link.href}\n`;
        });
      }

      containerText += `\n`; // Extra newline between containers
      finalText += containerText + "\n"; // Add to final text with separation
    });
  });

  if (finalText.trim() === "") {
    console.warn("No containers found to copy.");
    return;
  }

  // Copy to clipboard using the Clipboard API
  navigator.clipboard.writeText(finalText)
    .then(() => {
      console.log("Successfully copied containers text to clipboard!");
    })
    .catch(err => {
      console.error("Failed to copy text: ", err);
      // Fallback method using a temporary textarea
      const textarea = document.createElement("textarea");
      textarea.value = finalText;
      document.body.appendChild(textarea);
      textarea.select();
      try {
        document.execCommand("copy");
        console.log("Successfully copied containers text to clipboard (fallback method)!");
      } catch (e) {
        console.error("Failed to copy text (fallback method): ", e);
      }
      document.body.removeChild(textarea);
    });
}

findAndCopyTopPersonContainers("Lynn Loo");