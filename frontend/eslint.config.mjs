import eslint from "@eslint/js";
import tseslint from "typescript-eslint";

export default tseslint.config(
    eslint.configs.recommended,
    tseslint.configs.strictTypeChecked,
    tseslint.configs.stylisticTypeChecked,
    {
        languageOptions: {
            parserOptions: {
                projectService: true,
                tsconfigRootDir: import.meta.dirname
            }
        },
        linterOptions: {
            reportUnusedInlineConfigs: "warn"
        },
        rules: {
            "@typescript-eslint/no-non-null-assertion": "off",
            "@typescript-eslint/no-this-alias": "off",
            "@typescript-eslint/no-unused-vars": [
                "error",
                {
                    argsIgnorePattern: "^_",
                    varsIgnorePattern: "^_"
                }
            ]
        }
    }
);
