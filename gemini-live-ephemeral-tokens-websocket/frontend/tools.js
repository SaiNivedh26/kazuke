/**
 * Show Alert Box Tool
 * Displays a browser alert dialog with a custom message
 */
class ShowAlertTool extends FunctionCallDefinition {
  constructor() {
    super(
      "show_alert",
      "Displays an alert dialog box with a message to the user",
      {
        type: "object",
        properties: {
          message: {
            type: "string",
            description: "The message to display in the alert box"
          },
          title: {
            type: "string",
            description: "Optional title prefix for the alert message"
          }
        }
      },
      ["message"]
    );
  }

  functionToCall(parameters) {
    const message = parameters.message || "Alert!";
    const title = parameters.title;

    // Construct the full alert message
    const fullMessage = title ? `${title}: ${message}` : message;

    // Show the alert
    alert(fullMessage);

    console.log(` Alert shown: ${fullMessage}`);
  }
}
/**
 * Add CSS Style Tool
 * Injects CSS styles into the current page with !important flag
 */
class AddCSSStyleTool extends FunctionCallDefinition {
  constructor() {
    super(
      "add_css_style",
      "Injects CSS styles into the current page with !important flag",
      {
        type: "object",
        properties: {
          selector: {
            type: "string",
            description: "CSS selector to target elements (e.g., 'body', '.class', '#id')"
          },
          property: {
            type: "string",
            description: "CSS property to set (e.g., 'background-color', 'font-size', 'display')"
          },
          value: {
            type: "string",
            description: "Value for the CSS property (e.g., 'red', '20px', 'none')"
          },
          styleId: {
            type: "string",
            description: "Optional ID for the style element (for updating existing styles)"
          }
        }
      },
      ["selector", "property", "value"]
    );
  }

  functionToCall(parameters) {
    const { selector, property, value, styleId } = parameters;

    // Create or find the style element
    let styleElement;
    if (styleId) {
      styleElement = document.getElementById(styleId);
      if (!styleElement) {
        styleElement = document.createElement('style');
        styleElement.id = styleId;
        document.head.appendChild(styleElement);
      }
    } else {
      styleElement = document.createElement('style');
      document.head.appendChild(styleElement);
    }

    // Create the CSS rule with !important
    const cssRule = `${selector} { ${property}: ${value} !important; }`;

    // Add the CSS rule to the style element
    if (styleId) {
      // If using an ID, replace the content
      styleElement.textContent = cssRule;
    } else {
      // Otherwise append to any existing content
      styleElement.textContent += cssRule;
    }

    console.log(`🎨 CSS style injected: ${cssRule}`);
    console.log(`   Applied to ${document.querySelectorAll(selector).length} element(s)`);
  }
}

/**
 * Cognee Remember Tool
 * Stores info in shared knowledge graph. Returns instantly (background storage).
 */
class CogneeRememberTool extends FunctionCallDefinition {
  constructor() {
    super(
      "cognee_remember",
      "Stores important information, facts, or observations in persistent cross-session memory. Use when the user shares something worth remembering: preferences, objects, relationships, locations, sentimental items. Memory persists across all future sessions.",
      {
        type: "object",
        properties: {
          text: {
            type: "string",
            description: "The fact or observation to store in memory"
          }
        }
      },
      ["text"]
    );
  }

  async functionToCall(parameters) {
    const text = parameters.text;
    if (!text) return { error: "No text provided" };

    fetch("/api/cognee/remember", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text })
    }).catch(err => console.error("Cognee remember bg error:", err));

    console.log(`🧠 Memory queued: "${text}"`);
    return { status: "queued", message: "Memory will be stored in background" };
  }
}

/**
 * Cognee Batch Remember Tool
 * Stores multiple facts at once. Returns instantly (background storage).
 */
class CogneeBatchRememberTool extends FunctionCallDefinition {
  constructor() {
    super(
      "cognee_remember_batch",
      "Stores multiple facts at once in persistent cross-session memory. Use when you have several related facts to store together.",
      {
        type: "object",
        properties: {
          texts: {
            type: "array",
            items: { type: "string" },
            description: "Array of facts or observations to store"
          }
        }
      },
      ["texts"]
    );
  }

  async functionToCall(parameters) {
    const texts = parameters.texts;
    if (!texts || !Array.isArray(texts) || texts.length === 0) {
      return { error: "texts array is required" };
    }

    fetch("/api/cognee/remember_batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texts: texts })
    }).catch(err => console.error("Cognee batch bg error:", err));

    console.log(`🧠 Batch queued: ${texts.length} items`);
    return { status: "queued", count: texts.length };
  }
}

/**
 * Cognee Cognify Tool
 * Manually triggers graph rebuild on shared dataset.
 */
class CogneeCognifyTool extends FunctionCallDefinition {
  constructor() {
    super(
      "cognee_cognify",
      "Triggers the knowledge graph to rebuild with all stored memories. Call this when you need to ensure the graph is up to date before a recall query.",
      {
        type: "object",
        properties: {}
      },
      []
    );
  }

  async functionToCall(parameters) {
    try {
      const response = await fetch("/api/cognee/cognify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({})
      });

      const result = await response.json();

      if (!response.ok) {
        return { error: result.error || "Failed to cognify" };
      }

      console.log(`🔄 Graph rebuilt`);
      return { status: "cognified" };
    } catch (error) {
      return { error: error.message };
    }
  }
}

/**
 * Cognee Recall Tool
 * Searches the shared knowledge graph (cross-session).
 */
class CogneeRecallTool extends FunctionCallDefinition {
  constructor() {
    super(
      "cognee_recall",
      "Searches persistent cross-session memory for previously stored information. Use when the user asks about something from a past session or when you need facts stored earlier.",
      {
        type: "object",
        properties: {
          query: {
            type: "string",
            description: "The question or search query to find in memory"
          }
        }
      },
      ["query"]
    );
  }

  async functionToCall(parameters) {
    const query = parameters.query;
    if (!query) return { error: "No query provided" };

    try {
      const response = await fetch("/api/cognee/recall", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query })
      });

      const result = await response.json();

      if (!response.ok) {
        return { error: result.error || "Failed to recall memory" };
      }

      console.log(`🔍 Recall: "${query}" →`, result.result);
      return { result: result.result };
    } catch (error) {
      return { error: error.message };
    }
  }
}

/**
 * Cognee Forget Tool
 * Removes all data from the shared knowledge graph.
 */
class CogneeForgetTool extends FunctionCallDefinition {
  constructor() {
    super(
      "cognee_forget",
      "Removes ALL stored memories from the shared knowledge graph. Use only when the user explicitly wants to clear all memories.",
      {
        type: "object",
        properties: {
          confirm: {
            type: "boolean",
            description: "Confirmation to delete all memories"
          }
        }
      },
      ["confirm"]
    );
  }

  async functionToCall(parameters) {
    try {
      const response = await fetch("/api/cognee/forget", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({})
      });

      const result = await response.json();

      if (!response.ok) {
        return { error: result.error || "Failed to forget" };
      }

      console.log(`🗑️ All memories cleared`);
      addMessage(`[All memories cleared]`, "system");
      return { status: "forgotten" };
    } catch (error) {
      return { error: error.message };
    }
  }
}
