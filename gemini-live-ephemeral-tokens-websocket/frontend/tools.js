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

/**
 * Notion Search Tool
 * Searches Notion pages and databases
 */
class NotionSearchTool extends FunctionCallDefinition {
  constructor() {
    super(
      "notion_search",
      "Searches Notion for pages and databases matching a query. Returns pages with their IDs, titles, and metadata. Use this to find existing pages before creating new ones.",
      {
        type: "object",
        properties: {
          query: {
            type: "string",
            description: "The search query to match against page titles"
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
      const response = await fetch("/api/notion/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query })
      });

      const result = await response.json();

      if (!response.ok) {
        return { error: result.error || "Search failed" };
      }

      console.log(`🔍 Notion search: "${query}"`);
      return { result: result.result };
    } catch (error) {
      return { error: error.message };
    }
  }
}

/**
 * Notion Create Page Tool
 * Creates a new page in Notion
 */
class NotionCreatePageTool extends FunctionCallDefinition {
  constructor() {
    super(
      "notion_create_page",
      "Creates a new page in Notion with a title and content. Optionally specify a parent_id to create it under an existing page. Returns the new page ID.",
      {
        type: "object",
        properties: {
          title: {
            type: "string",
            description: "The title of the new page"
          },
          content: {
            type: "string",
            description: "The content/body of the page (plain text or markdown)"
          },
          parent_id: {
            type: "string",
            description: "Optional: ID of parent page to create under (if not provided, creates at workspace root)"
          }
        }
      },
      ["title", "content"]
    );
  }

  async functionToCall(parameters) {
    const { title, content, parent_id } = parameters;
    if (!title || !content) return { error: "Title and content are required" };

    try {
      const body = { title, content };
      if (parent_id) body.parent_id = parent_id;

      const response = await fetch("/api/notion/create_page", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });

      const result = await response.json();

      if (!response.ok) {
        return { error: result.error || "Create page failed" };
      }

      console.log(`📝 Notion page created: "${title}"`);
      addMessage(`[Notion page created: "${title}"]`, "system");
      return { result: result.result };
    } catch (error) {
      return { error: error.message };
    }
  }
}

/**
 * Notion Append Tool
 * Appends content to an existing Notion page
 */
class NotionAppendTool extends FunctionCallDefinition {
  constructor() {
    super(
      "notion_append_to_page",
      "Appends content to an existing Notion page. Use the page ID from search results or from creating a page.",
      {
        type: "object",
        properties: {
          page_id: {
            type: "string",
            description: "The ID of the Notion page to append to"
          },
          content: {
            type: "string",
            description: "The content to append (plain text or markdown)"
          }
        }
      },
      ["page_id", "content"]
    );
  }

  async functionToCall(parameters) {
    const { page_id, content } = parameters;
    if (!page_id || !content) return { error: "page_id and content are required" };

    try {
      const response = await fetch("/api/notion/append", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ page_id, content })
      });

      const result = await response.json();

      if (!response.ok) {
        return { error: result.error || "Append failed" };
      }

      console.log(`📝 Appended to Notion page: ${page_id}`);
      addMessage(`[Content added to Notion page]`, "system");
      return { result: result.result };
    } catch (error) {
      return { error: error.message };
    }
  }
}

/**
 * Notion Get Page Tool
 * Gets content from a specific Notion page as markdown
 */
class NotionGetPageTool extends FunctionCallDefinition {
  constructor() {
    super(
      "notion_get_page",
      "Retrieves the content of a specific Notion page as markdown. Use with a page ID from search results.",
      {
        type: "object",
        properties: {
          page_id: {
            type: "string",
            description: "The ID of the Notion page to retrieve"
          }
        }
      },
      ["page_id"]
    );
  }

  async functionToCall(parameters) {
    const page_id = parameters.page_id;
    if (!page_id) return { error: "No page_id provided" };

    try {
      const response = await fetch("/api/notion/get_page", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ page_id })
      });

      const result = await response.json();

      if (!response.ok) {
        return { error: result.error || "Get page failed" };
      }

      console.log(`📄 Notion page retrieved: ${page_id}`);
      return { result: result.result };
    } catch (error) {
      return { error: error.message };
    }
  }
}

/**
 * Composio Slack Send Message Tool
 * Sends a message to a Slack channel via Composio
 */
class SlackSendMessageTool extends FunctionCallDefinition {
  constructor() {
    super(
      "slack_send_message",
      "Sends a message to a Slack channel. Use when the user asks to send a message, notify, or post to Slack.",
      {
        type: "object",
        properties: {
          channel: {
            type: "string",
            description: "The Slack channel name or ID (e.g., 'general', '#random')"
          },
          message: {
            type: "string",
            description: "The message text to send"
          }
        }
      },
      ["channel", "message"]
    );
  }

  async functionToCall(parameters) {
    const { channel, message } = parameters;
    if (!channel || !message) return { error: "channel and message are required" };

    try {
      const response = await fetch("/api/composio/call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tool_name: "SLACK_SEND_MESSAGE",
          arguments: { channel, markdown_text: message }
        })
      });

      const result = await response.json();

      if (!response.ok) {
        return { error: result.error || "Failed to send message" };
      }

      console.log(`💬 Slack message sent to ${channel}`);
      addMessage(`[Message sent to Slack: ${channel}]`, "system");
      return { result: result.result };
    } catch (error) {
      return { error: error.message };
    }
  }
}

/**
 * Composio Slack List Channels Tool
 * Lists all Slack channels via Composio
 */
class SlackListChannelsTool extends FunctionCallDefinition {
  constructor() {
    super(
      "slack_list_channels",
      "Lists all available Slack channels. Use to find channel names before sending messages.",
      {
        type: "object",
        properties: {
          limit: {
            type: "integer",
            description: "Maximum number of channels to return (default: 100)"
          }
        }
      },
      []
    );
  }

  async functionToCall(parameters) {
    try {
      const response = await fetch("/api/composio/call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tool_name: "SLACK_LIST_ALL_CHANNELS",
          arguments: { limit: parameters.limit || 100 }
        })
      });

      const result = await response.json();

      if (!response.ok) {
        return { error: result.error || "Failed to list channels" };
      }

      console.log(`📋 Slack channels listed`);
      return { result: result.result };
    } catch (error) {
      return { error: error.message };
    }
  }
}

/**
 * Composio Gmail Fetch Tool
 * Fetches emails from Gmail via Composio
 */
class GmailFetchTool extends FunctionCallDefinition {
  constructor() {
    super(
      "gmail_fetch_emails",
      "Fetches emails from Gmail. Use when the user asks to check emails, read messages, or search inbox.",
      {
        type: "object",
        properties: {
          query: {
            type: "string",
            description: "Optional search query (e.g., 'from:john', 'subject:meeting', 'is:unread')"
          },
          max_results: {
            type: "integer",
            description: "Maximum number of emails to fetch (default: 10)"
          }
        }
      },
      []
    );
  }

  async functionToCall(parameters) {
    const query = parameters.query;
    const max_results = parameters.max_results || 10;

    try {
      const arguments_obj = { max_results };
      if (query) arguments_obj.query = query;

      const response = await fetch("/api/composio/call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tool_name: "GMAIL_FETCH_EMAILS",
          arguments: arguments_obj
        })
      });

      const result = await response.json();

      if (!response.ok) {
        return { error: result.error || "Failed to fetch emails" };
      }

      console.log(`📧 Gmail emails fetched`);
      return { result: result.result };
    } catch (error) {
      return { error: error.message };
    }
  }
}

/**
 * Composio Gmail Send Tool
 * Sends an email via Gmail through Composio
 */
class GmailSendTool extends FunctionCallDefinition {
  constructor() {
    super(
      "gmail_send_email",
      "Sends an email via Gmail. Use when the user asks to send an email or compose a message.",
      {
        type: "object",
        properties: {
          to: {
            type: "string",
            description: "Recipient email address"
          },
          subject: {
            type: "string",
            description: "Email subject"
          },
          body: {
            type: "string",
            description: "Email body content"
          }
        }
      },
      ["to", "subject", "body"]
    );
  }

  async functionToCall(parameters) {
    const { to, subject, body } = parameters;
    if (!to || !subject || !body) return { error: "to, subject, and body are required" };

    try {
      const response = await fetch("/api/composio/call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tool_name: "GMAIL_SEND_EMAIL",
          arguments: { to, subject, body }
        })
      });

      const result = await response.json();

      if (!response.ok) {
        return { error: result.error || "Failed to send email" };
      }

      console.log(`📧 Email sent to ${to}`);
      addMessage(`[Email sent to ${to}]`, "system");
      return { result: result.result };
    } catch (error) {
      return { error: error.message };
    }
  }
}

/**
 * Composio Calendar Get Events Tool
 * Gets Google Calendar events via Composio
 */
class CalendarGetEventsTool extends FunctionCallDefinition {
  constructor() {
    super(
      "calendar_get_events",
      "Gets events from Google Calendar. Use when the user asks about their schedule, upcoming events, or calendar.",
      {
        type: "object",
        properties: {
          time_min: {
            type: "string",
            description: "Start time in ISO format (e.g., '2025-01-08T00:00:00Z')"
          },
          time_max: {
            type: "string",
            description: "End time in ISO format (e.g., '2025-01-08T23:59:59Z')"
          },
          max_results: {
            type: "integer",
            description: "Maximum number of events to fetch (default: 10)"
          }
        }
      },
      []
    );
  }

  async functionToCall(parameters) {
    const { time_min, time_max, max_results } = parameters;

    try {
      const arguments_obj = { max_results: max_results || 10 };
      if (time_min) arguments_obj.time_min = time_min;
      if (time_max) arguments_obj.time_max = time_max;

      const response = await fetch("/api/composio/call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tool_name: "GOOGLECALENDAR_EVENTS_LIST",
          arguments: arguments_obj
        })
      });

      const result = await response.json();

      if (!response.ok) {
        return { error: result.error || "Failed to get events" };
      }

      console.log(`📅 Calendar events fetched`);
      return { result: result.result };
    } catch (error) {
      return { error: error.message };
    }
  }
}

/**
 * Composio Calendar Create Event Tool
 * Creates a new event in Google Calendar via Composio
 */
class CalendarCreateEventTool extends FunctionCallDefinition {
  constructor() {
    super(
      "calendar_create_event",
      "Creates a new event in Google Calendar. Use when the user asks to schedule, create, or add an event.",
      {
        type: "object",
        properties: {
          summary: {
            type: "string",
            description: "Event title"
          },
          start_datetime: {
            type: "string",
            description: "Start time in ISO 8601 format (e.g., '2025-01-08T10:00:00')"
          },
          timezone: {
            type: "string",
            description: "IANA timezone (e.g., 'Asia/Kolkata' for IST, 'America/New_York' for EST). Default: 'Asia/Kolkata' (IST)"
          },
          end_datetime: {
            type: "string",
            description: "End time in ISO 8601 format (e.g., '2025-01-08T11:00:00'). Optional - if not provided, uses duration"
          },
          event_duration_hour: {
            type: "integer",
            description: "Duration in hours (0-240). Default: 1"
          },
          event_duration_minutes: {
            type: "integer",
            description: "Duration in minutes (0-59). Default: 0"
          },
          description: {
            type: "string",
            description: "Optional event description"
          }
        }
      },
      ["summary", "start_datetime"]
    );
  }

  async functionToCall(parameters) {
    const { summary, start_datetime, timezone, end_datetime, event_duration_hour, event_duration_minutes, description } = parameters;
    if (!summary || !start_datetime) {
      return { error: "summary and start_datetime are required" };
    }

    try {
      const arguments_obj = {
        summary,
        start_datetime,
        timezone: timezone || "Asia/Kolkata"
      };
      
      if (end_datetime) {
        arguments_obj.end_datetime = end_datetime;
      } else {
        arguments_obj.event_duration_hour = event_duration_hour !== undefined ? event_duration_hour : 1;
        arguments_obj.event_duration_minutes = event_duration_minutes !== undefined ? event_duration_minutes : 0;
      }
      
      if (description) arguments_obj.description = description;

      const response = await fetch("/api/composio/call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tool_name: "GOOGLECALENDAR_CREATE_EVENT",
          arguments: arguments_obj
        })
      });

      const result = await response.json();

      if (!response.ok) {
        return { error: result.error || "Failed to create event" };
      }

      console.log(`📅 Calendar event created: "${summary}"`);
      addMessage(`[Calendar event created: "${summary}"]`, "system");
      return { result: result.result };
    } catch (error) {
      return { error: error.message };
    }
  }
}

/**
 * Composio Calendar Delete Event Tool
 * Deletes an event from Google Calendar via Composio
 */
class CalendarDeleteEventTool extends FunctionCallDefinition {
  constructor() {
    super(
      "calendar_delete_event",
      "Deletes an event from Google Calendar. Use when the user asks to delete, remove, or cancel an event.",
      {
        type: "object",
        properties: {
          event_id: {
            type: "string",
            description: "The ID of the event to delete"
          },
          calendar_id: {
            type: "string",
            description: "Calendar ID (default: 'primary')"
          }
        }
      },
      ["event_id"]
    );
  }

  async functionToCall(parameters) {
    const { event_id, calendar_id } = parameters;
    if (!event_id) {
      return { error: "event_id is required" };
    }

    try {
      const arguments_obj = {
        event_id,
        calendar_id: calendar_id || "primary"
      };

      const response = await fetch("/api/composio/call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tool_name: "GOOGLECALENDAR_DELETE_EVENT",
          arguments: arguments_obj
        })
      });

      const result = await response.json();

      if (!response.ok) {
        return { error: result.error || "Failed to delete event" };
      }

      console.log(`🗑️ Calendar event deleted: ${event_id}`);
      addMessage(`[Calendar event deleted]`, "system");
      return { result: result.result };
    } catch (error) {
      return { error: error.message };
    }
  }
}
