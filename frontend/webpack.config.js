const path = require("path");
const HtmlWebpackPlugin = require("html-webpack-plugin");

module.exports = {
    mode: "development",
    entry: "./src/index.ts",
    module: {
        rules: [
            {
                test: /\.tsx?$/,
                use: "ts-loader",
                exclude: /node_modules/
            },
            {
                test: /\.css$/,
                use: ["style-loader", "css-loader"]
            }
        ]
    },
    resolve: {
        extensions: [".tsx", ".ts", ".js"]
    },
    plugins: [new HtmlWebpackPlugin({ template: "src/index.html" })],
    devtool: "inline-source-map",
    devServer: {
        static: "./dist",
        proxy: [
            {
                context: ["/aggregator"],
                target: "ws://aggregator:9999",
                ws: true
            }
        ]
    },
    output: {
        filename: "[name].bundle.js",
        path: path.resolve(__dirname, "dist"),
        clean: true
    },
    optimization: {
        runtimeChunk: "single"
    }
};
