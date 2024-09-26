package main

import (
    "bufio"
    "compress/gzip"
    "flag"
    "fmt"
    "io"
    "os"
    "regexp"
    "strings"
    "sync"
)

// Load patterns from a file
func loadPatterns(filename string) ([]string, error) {
    file, err := os.Open(filename)
    if err != nil {
        return nil, err
    }
    defer file.Close()

    var patterns []string
    scanner := bufio.NewScanner(file)
    for scanner.Scan() {
        pattern := strings.TrimSpace(scanner.Text())
        if pattern != "" {
            patterns = append(patterns, pattern)
        }
    }

    if err := scanner.Err(); err != nil {
        return nil, err
    }

    return patterns, nil
}

// Check if the line matches any exclusion patterns
func isExcluded(line string, notAnError *regexp.Regexp) bool {
    return notAnError.MatchString(line)
}

// Check if the line matches any error patterns and write to output if found
func checkLine(line string, errorPattern, notAnError *regexp.Regexp, mu *sync.Mutex, wg *sync.WaitGroup, output *os.File, outputToFile bool) {
    defer wg.Done()
    if errorPattern.MatchString(line) && !isExcluded(line, notAnError) {
        mu.Lock()
        if outputToFile {
            output.WriteString(line + "\n") // Write to file
        } else {
            fmt.Println("Found error:", line) // Print to console
        }
        mu.Unlock()
    }
}

// Process the log file
func processLogFile(logFile string, errorPatterns, notErrorPatterns []string, outputFile *os.File, outputToFile bool) {
    file, err := os.Open(logFile)
    if err != nil {
        fmt.Println("Error opening log file:", err)
        return
    }
    defer file.Close()

    var reader io.Reader

    // Check if the file is gzipped
    if strings.HasSuffix(logFile, ".gz") {
        gzipReader, err := gzip.NewReader(file)
        if err != nil {
            fmt.Println("Error opening gzip file:", err)
            return
        }
        defer gzipReader.Close()
        reader = gzipReader
    } else {
        reader = file
    }

    bufReader := bufio.NewReader(reader)
    var wg sync.WaitGroup
    var mu sync.Mutex

    // Combine all error patterns into one regex
    combinedErrorPattern := strings.Join(errorPatterns, "|")
    errorRegex := regexp.MustCompile(combinedErrorPattern)

    // Combine all not-error patterns into one regex
    combinedNotErrorPattern := strings.Join(notErrorPatterns, "|")
    notErrorRegex := regexp.MustCompile(combinedNotErrorPattern)

    // Read and check each line
    for {
        line, err := bufReader.ReadString('\n')
        if err != nil {
            if err == io.EOF {
                break // Exit loop on EOF
            }
            fmt.Println("Error reading log file:", err)
            return
        }
        wg.Add(1)
        go checkLine(strings.TrimSpace(line), errorRegex, notErrorRegex, &mu, &wg, outputFile, outputToFile)
    }

    wg.Wait() // Wait for all goroutines to finish
}

func main() {
    // Define command-line flags
    logFile := flag.String("log", "", "Path to the log file (supports .gz files)")
    errorsFile := flag.String("errors", "errors.txt", "Path to the error patterns file")
    notErrorsFile := flag.String("ignore", "", "Path to the ignore patterns file")
    outputFile := flag.String("output", "", "Path to the output file for found errors")
    flag.Parse()

    // Validate input
    if *logFile == "" {
        fmt.Println("Log file must be specified using --log")
        return
    }

    // Load error patterns from the specified file
    errorPatterns, err := loadPatterns(*errorsFile)
    if err != nil {
        fmt.Printf("Error loading error patterns from %s: %v\n", *errorsFile, err)
        return
    }

    // Load not-error patterns from the specified file if provided
    var notErrorPatterns []string
    if *notErrorsFile != "" {
        notErrorPatterns, err = loadPatterns(*notErrorsFile)
        if err != nil {
            fmt.Printf("Error loading not error patterns from %s: %v\n", *notErrorsFile, err)
            return
        }
    }

    // Determine if we are writing to an output file or printing to the console
    outputToFile := false
    var output *os.File

    if *outputFile != "" {
        outputToFile = true
        output, err = os.Create(*outputFile)
        if err != nil {
            fmt.Printf("Error creating output file %s: %v\n", *outputFile, err)
            return
        }
        defer output.Close()
    }

    processLogFile(*logFile, errorPatterns, notErrorPatterns, output, outputToFile)
}

