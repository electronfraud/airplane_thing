import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";

@customElement("stale-indicator")
export default class StaleIndicator extends LitElement {
    @property({ type: String })
    status = "ok";

    @property({ type: String })
    howLong = "0s";

    static styles = css`
        .outer.ok {
            display: none;
        }
        .outer {
            position: absolute;
            top: 1ch;
            left: 1ch;
            border: 2px solid red;
            color: red;
            text-align: center;
            width: 30ch;
        }
        .message {
            font-family: "Roboto Mono", monospace;
            font-weight: bold;
            font-size: 300%;
        }
        .how-long {
            font-family: "Raleway", sans-serif;
            padding: 0 1ch 1ch 1ch;
        }
    `;

    render() {
        return html`
            <div class="outer ${this.status}">
                <div class="message">NO DATA</div>
                <div class="how-long">Last update ${this.howLong} ago</div>
            </div>
        `;
    }
}
