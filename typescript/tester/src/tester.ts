#!/usr/bin/env node
/**
 * An integration testing script for the SOL26 interpreter.
 *
 * IPP: You can implement the entire tool in this file if you wish, but it is recommended to split
 *      the code into multiple files and modules as you see fit.
 *
 *      Below, you have some code to get you started with the CLI argument parsing and logging setup,
 *      but you are **free to modify it** in whatever way you like.
 *
 * Author: Ondřej Ondryáš <iondryas@fit.vut.cz>
 *
 * AI usage notice: The author used OpenAI Codex to create the implementation of this
 *                  module based on its Python counterpart.
 */

import { existsSync, lstatSync, writeFileSync, readdirSync, readFileSync, unlink } from "node:fs";
import { basename, dirname, resolve, join } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

import { TestCaseDefinition, TestCaseReport, TestCaseType, TestReport, TestResult, CategoryReport} from "./models.js";

import { spawnSync } from "node:child_process";

import { pino } from "pino";

const logger = pino({
  transport: {
    target: "pino-pretty",
    options: {
      colorize: true,
      destination: 2,
    },
  },
});

interface CliArguments {
  tests_dir: string;
  recursive: boolean;
  output: string | null;
  dry_run: boolean;
  include: string[] | null;
  include_category: string[] | null;
  include_test: string[] | null;
  exclude: string[] | null;
  exclude_category: string[] | null;
  exclude_test: string[] | null;
  verbose: number;
  regex_filters: boolean;
}

function writeResult(resultReport: TestReport, outputFile: string | null): void {
  /**
   * Writes the final report to the specified output file or standard output if no file is provided.
   */
  const resultJson = JSON.stringify(resultReport, null, 2);
  if (outputFile !== null) {
    writeFileSync(outputFile, resultJson, "utf8");
    return;
  }

  console.log(resultJson);
}

const DOUBLE_LETTER_SHORT_OPTION_NORMALIZATION = new Map<string, string>([
  ["-ic", "--include-category"],
  ["-it", "--include-test"],
  ["-ec", "--exclude-category"],
  ["-et", "--exclude-test"],
]);

const HELP_TEXT = [
  "Usage:",
  "  tester [options] tests_dir",
  "",
  "Positional arguments:",
  "  tests_dir                 Path to a directory with the test cases in the SOLtest format.",
  "",
  "Options:",
  "  -h, --help                Show this help message and exit.",
  "  -r, --recursive           Recursively search for test cases in subdirectories of the provided directory.",
  "  -o, --output <path>       The output file to write the test results to. If not provided, results will be printed to standard output.",
  "  --dry-run                 Perform a dry run: discover the test cases but don't actually execute them.",
  "  -i, --include <value>     Include only test cases with the specified name or category. Can be used multiple times to specify multiple criteria.Can be combined with -ic and -it.",
  "  -ic, --include-category <value>",
  "                            Include only test cases with the specified category. Can be used multiple times to specify multiple accepted categories. Can be combined with -it and -i.",
  "  -it, --include-test <value>",
  "                            Include only test cases with the specified name. Can be used multiple times to specify multiple accepted names. Can be combined with -ic and -i.",
  "  -e, --exclude <value>     Exclude test cases with the specified name or category. Can be used multiple times to specify multiple criteria.Can be combined with -ic and -it.",
  "  -ec, --exclude-category <value>",
  "                            Exclude test cases with the specified category. Can be used multiple times to specify multiple accepted categories. Can be combined with -it and -i.",
  "  -et, --exclude-test <value>",
  "                            Exclude test cases with the specified name. Can be used multiple times to specify multiple accepted names. Can be combined with -ic and -i.",
  "  -g                        When used, the filters specified with -i[ct]/-e[ct] will be interpreted as regular expressions instead of literal strings.",
  "  -v, --verbose             Enable verbose logging output (using once = INFO level, using twice = DEBUG level).",
];

const PARSE_OPTIONS = {
  help: { type: "boolean", short: "h", default: false },
  recursive: { type: "boolean", short: "r", default: false },
  output: { type: "string", short: "o" },
  "dry-run": { type: "boolean", default: false },
  include: { type: "string", short: "i", multiple: true },
  "include-category": { type: "string", multiple: true },
  "include-test": { type: "string", multiple: true },
  exclude: { type: "string", short: "e", multiple: true },
  "exclude-category": { type: "string", multiple: true },
  "exclude-test": { type: "string", multiple: true },
  "regex-filters": { type: "boolean", short: "g", default: false },
  verbose: { type: "boolean", short: "v", multiple: true },
} as const;

function normalizeArgv(argv: string[]): string[] {
  return argv.map((arg) => DOUBLE_LETTER_SHORT_OPTION_NORMALIZATION.get(arg) ?? arg);
}

function printHelp(): void {
  console.log(HELP_TEXT.join("\n"));
}

function listOrNull(values: string[] | undefined): string[] | null {
  if (values === undefined || values.length === 0) {
    return null;
  }

  return values;
}

function parseCliArgumentsRaw(argv: string[]) {
  return parseArgs({
    args: normalizeArgv(argv),
    options: PARSE_OPTIONS,
    allowPositionals: true,
    strict: true,
  } as const);
}

function parseArguments(): CliArguments {
  /**
   * Parses the command-line arguments and performs basic validation a sanitization.
   */
  let parsed: ReturnType<typeof parseCliArgumentsRaw>;

  try {
    parsed = parseCliArgumentsRaw(process.argv.slice(2));
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(message);
    process.exit(2);
  }

  const parsedValues = parsed.values;

  if (parsedValues["help"]) {
    printHelp();
    process.exit(0);
  }

  if (parsed.positionals.length !== 1 || parsed.positionals[0] === undefined) {
    console.error("Exactly one positional argument (tests_dir) is required.");
    process.exit(2);
  }

  const args: CliArguments = {
    tests_dir: resolve(parsed.positionals[0]),
    recursive: parsedValues["recursive"],
    output: parsedValues["output"] ?? null,
    dry_run: parsedValues["dry-run"],
    include: listOrNull(parsedValues["include"]),
    include_category: listOrNull(parsedValues["include-category"]),
    include_test: listOrNull(parsedValues["include-test"]),
    exclude: listOrNull(parsedValues["exclude"]),
    exclude_category: listOrNull(parsedValues["exclude-category"]),
    exclude_test: listOrNull(parsedValues["exclude-test"]),
    verbose: parsedValues["verbose"]?.length ?? 0,
    regex_filters: parsedValues["regex-filters"],
  };

  // Check source directory
  if (!existsSync(args.tests_dir) || !lstatSync(args.tests_dir).isDirectory()) {
    console.error("The provided path is not a directory.");
    process.exit(1);
  }

  // Warn if the output file already exists
  if (args.output !== null) {
    const outputParent = dirname(args.output);
    if (!existsSync(outputParent)) {
      console.error("The parent directory of the output file does not exist.");
      process.exit(1);
    }

    if (existsSync(args.output)) {
      logger.warn("The output file will be overwritten: %s", args.output);
    }
  }

  return args;
}

function main(): void {
  /**
   * The main entry point for the SOL26 integration testing script.
   * It parses command-line arguments and executes the testing process.
   */

  // Set up logging
  // IPP: You do not have to use logging - but it is the recommended practice.
  //      See https://getpino.io/#/docs/api for more information.
  logger.level = "warn";

  // Parse the CLI arguments
  const args = parseArguments();

  // Enable debug or info logging if the verbose flag was set twice or once
  if (args.verbose >= 2) {
    logger.level = "debug";
  } else if (args.verbose === 1) {
    logger.level = "info";
  }

  // TODO: Your code for discovering and executing the test cases goes here.
  
  for (const key in args) {
    logger.debug("Argument %s: %o", key, args[key as keyof CliArguments]);
  }

  const tests = discoverTests(args.tests_dir, args.recursive);

  const discovered_test_cases: TestCaseDefinition[] = [];
  for (const test of tests) {
    logger.info("Discovered test: %s", test);
    let parsed_test = parseTest(test);
    if (parsed_test) {
      discovered_test_cases.push(parsed_test);
    } else {
      logger.warn("Failed to parse test case file: %s", test);
    }
  }

  const test_categories: Record<string, { total: number; passed: number; test_results: Record<string, TestCaseReport> }> = {};


  for (const test_case of discovered_test_cases) {
    const report = runTest(test_case);
    logger.info("Test case %s resulted in: %o", test_case.name, report);

    const category = test_case.category;

    if(!test_categories[category]) {
      test_categories[category] = { total: 0, passed: 0, test_results: {} };
    }

    test_categories[category].test_results[test_case.name] = report;
    test_categories[category].total += test_case.points;
    if (report.result === TestResult.PASSED) {
      test_categories[category].passed += test_case.points;
    }
  }

  const results: Record<string, CategoryReport> = {};
  for (const category in test_categories) {
    const entry = test_categories[category]!; // i hope this wont bite me in the ... :3
    results[category] = new CategoryReport(entry.total, entry.passed, entry.test_results);
  }

  // // todo unexecuted
  const report = new TestReport({ discovered_test_cases, unexecuted: {}, results });
  writeResult(report, args.output);

  logger.debug("End of program");
}

function discoverTests(directory: string, recursive: boolean) : string[] {
  let tests: string[] = [];
  readdirSync(directory, { withFileTypes: true }).forEach((entry) => {
    if (entry.isDirectory() && recursive) {
      tests = tests.concat(discoverTests(resolve(directory, entry.name), recursive));
    }
    else if (entry.isFile() && entry.name.endsWith(".test")) {
      tests.push(resolve(directory, entry.name));
    }
  });
  return tests; 
}

function parseTest(testPath: string): TestCaseDefinition{
    let test_type: TestCaseType = TestCaseType.COMBINED;
    let description: string | null = null;
    let category: string | null = null;
    let points: number = 0;
    let expected_parser_exit_codes: number[] | null = [];
    let expected_interpreter_exit_codes: number[] | null = [];

    readFileSync(testPath, "utf8").split("\n").forEach((line) => {
    logger.debug("Test line: %s", line);

    if(line.startsWith("***")) {
      description = line.substring(3).trim();
    }
    else if(line.startsWith("+++")) {
      category = line.substring(3).trim();
    }
    else if(line.startsWith("!C!")) {
      expected_parser_exit_codes.push(parseInt(line.substring(3).trim()));
    }
    else if(line.startsWith("!I!")) {
      expected_interpreter_exit_codes.push(parseInt(line.substring(3).trim()));
    }
    else if(line.startsWith(">>>")) {
      points = parseInt(line.substring(3).trim());
    }
  });

    if(expected_interpreter_exit_codes.length > 0 && expected_parser_exit_codes.length > 0) {
      test_type = TestCaseType.COMBINED;
    } else if (expected_interpreter_exit_codes.length > 0) {
      test_type = TestCaseType.EXECUTE_ONLY;
    } else if (expected_parser_exit_codes.length > 0) {
      test_type = TestCaseType.PARSE_ONLY;
    } else {
      // TODO maybe have default one or exit here
      // okay so i changed it so that COMBINED is default, but i will leave this else here
      logger.warn("No test case specified for test file %s", testPath);
    }

    let name = basename(testPath, ".test");
    let stdin_file: string | null = resolve(dirname(testPath), name + ".in");
    let expected_stdout_file: string | null = resolve(dirname(testPath), name + ".out");
    
    if (!existsSync(stdin_file)) {
      stdin_file = null;
    }

    if (!existsSync(expected_stdout_file)) {
      expected_stdout_file = null;
    }


    return new TestCaseDefinition({
      name,
      test_source_path: testPath,
      stdin_file,
      expected_stdout_file,
      test_type,
      description,
      category: category ?? "uncategorized",
      points,
      // todo write this better :3
      expected_parser_exit_codes: expected_parser_exit_codes?.length ? expected_parser_exit_codes : null,
      expected_interpreter_exit_codes: expected_interpreter_exit_codes?.length ? expected_interpreter_exit_codes : null,
    
  });
}

function runTest(test_case: TestCaseDefinition) : TestCaseReport {
  const lines = readFileSync(test_case.test_source_path, "utf8").split("\n");
  const empty_line = lines.findIndex(line => line.trim() === "");

  const source_code = lines.slice(empty_line + 1).join("\n");

  logger.debug("Running test case %s with source code:\n%s", test_case.name, source_code);

  if(source_code.startsWith('<?xml version="1.0" encoding="UTF-8"?>')) {
    logger.info("Source code is XML");
  } else {
    logger.info("Source code is SOL26");
    let converted_code = convertToXml(source_code);
    
    logger.debug("Converted code:\n%s", converted_code);

    let result = runInterpreter(converted_code, test_case.stdin_file);
    logger.debug("Interpreter stdout:\n%s", result.stdout);
    logger.debug("Interpreter exit code: %s", result.exit_code);
    logger.debug("Interpreter stderr:\n%s", result.stderr);
    
    const exit_code_comparison = compareExitCode(result.exit_code, test_case.expected_interpreter_exit_codes);
    if (!exit_code_comparison) {
      logger.info("Test case %s failed: exit code", test_case.name);
      return new TestCaseReport(
      TestResult.UNEXPECTED_INTERPRETER_EXIT_CODE,
      null,
      result.exit_code,
      null,
      null,
      result.stdout,
      result.stderr,
      null
    );
    }

    if (test_case.expected_stdout_file && result.exit_code === 0) {
      const stdout_comparison = compareStdout(result.stdout, test_case.expected_stdout_file);
      if (!stdout_comparison) {
        logger.info("Test case %s failed: stdout", test_case.name);
        return new TestCaseReport(
          TestResult.INTERPRETER_RESULT_DIFFERS,
          null,
          result.exit_code,
          null,
          null,
          result.stdout,
          result.stderr,
          null
        );
      }
    }

    logger.info("Test case %s passed", test_case.name);
    return new TestCaseReport(
      TestResult.PASSED,
      null,
      result.exit_code,
      null,
      null,
      result.stdout,
      result.stderr,
      null
    );
  }

  // shouldnt get here?
  logger.error("shouldnt get here");
  return new TestCaseReport(
    TestResult.UNEXPECTED_PARSER_EXIT_CODE,
    null,
    null,
    null,
    null,
    null,
    null,
    null
   );
}

function convertToXml(sol26_code: string): string {
  // logger.debug("Converting SOL26 code to XML:\n%s", sol26_code);

  const currentDir = dirname(fileURLToPath(import.meta.url));
  // TODO make this better not with hardcoded paths :3
  const sol2xmlPath = resolve(currentDir, "../../../sol2xml/sol_to_xml.py");
  const pythonPath = resolve(currentDir, "../../../.venv/bin/python3");
  const convert = spawnSync(pythonPath, [sol2xmlPath], { input: sol26_code, encoding: "utf8" });
  
  if (convert.error) {
    logger.error("Error executing sol2xml.py");
    return "";
  }

  if (convert.status !== 0) {
    logger.error("sol2 exited with error status %s", convert.stderr);
    return "";
  }

  return convert.stdout;
}

interface InterpreterResult {
  stdout: string;
  stderr: string;
  exit_code: number | null;
}

function runInterpreter(xml_code: string, stdin_file: string | null): InterpreterResult {
  logger.debug("Running interpreter");

  const currentDir = dirname(fileURLToPath(import.meta.url));
  const interpreterPath = resolve(currentDir, "../../../python/int/src/solint.py");
  const pythonPath = resolve(currentDir, "../../../.venv/bin/python3");
  
  const tempFile = join(currentDir, "temp_code.xml");
  writeFileSync(tempFile, xml_code, "utf8");

  let args: string[];
  if(stdin_file) {
    logger.debug("Using stdin file: %s", stdin_file);
    args = [interpreterPath, "-s", tempFile, "-i", stdin_file];
  } else {
    logger.debug("No stdin file provided, no input used");
    args = [interpreterPath, "-s", tempFile];
  }


  const result = spawnSync(pythonPath, args, { input: xml_code, encoding: "utf8" });

  unlink(tempFile, (err) => {
    if (err) {
      logger.error("Failed to delete temporary file: %s", tempFile);
    }
  });

  // logger.debug("Interpreter execution result: %o", result);
  // logger.debug("Interpreter status: %s", result.status);
  // logger.debug("Interpreter stdout:\n%s", result.stdout);
  // logger.debug("Interpreter stderr:\n%s", result.stderr);

  return {stdout: result.stdout, stderr: result.stderr, exit_code: result.status};
}

function compareStdout(actual: string, expectedFile: string | null): boolean {
  if (expectedFile === null) {
    logger.warn("No expected stdout file provided for comparison.");
    return false;
  }
  
  const tempoutput = join(dirname(fileURLToPath(import.meta.url)), "temp_output.txt");
  writeFileSync(tempoutput, actual, "utf8");

  const diffResult = spawnSync("diff", [ tempoutput, expectedFile], { encoding: "utf8" });

  unlink(tempoutput, (err) => {
    if (err) {
      logger.error("Failed to delete temporary file: %s", tempoutput);
    }
  });

  if (diffResult.error) {
    logger.error("Error executing diff command");
    return false;
  }

  if (diffResult.status === 0) {
    return true;
  } else {
    logger.info("Diff: %s", diffResult.stdout);
    return false;
  }
}

function compareExitCode(actual: number | null, expected: number[] | null): boolean {
  if (expected === null) {
    logger.warn("No expected exit codes provided for comparison.");
    return false;
  }

  if (actual === null) {
    logger.warn("Actual exit code is null, cannot compare.");
    return false;
  }

  return expected.includes(actual);
}

main();
