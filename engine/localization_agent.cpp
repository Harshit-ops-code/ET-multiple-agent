#include <iostream>
#include <string>
#include <vector>
#include <sstream>

int main(int argc, char* argv[]) {
    // 1. Check if languages were passed from Python
    if (argc < 2) {
        std::cerr << "Error: No target languages provided." << std::endl;
        return 1;
    }

    // 2. Parse the target languages (comma-separated string from Python)
    std::string langs_str = argv[1];
    std::vector<std::string> languages;
    std::stringstream ss(langs_str);
    std::string lang;
    
    while (std::getline(ss, lang, ',')) {
        languages.push_back(lang);
    }

    // 3. Read the full approved blog content passed from Python via Standard Input
    std::string content;
    std::string line;
    while (std::getline(std::cin, line)) {
        content += line + "\n";
    }

    // 4. Process and simulate translation for each language
    for (size_t i = 0; i < languages.size(); ++i) {
        std::string target_lang = languages[i];
        
        // We use these delimiters so your Python wrapper can parse the output cleanly
        std::cout << "===START_LANG:" << target_lang << "===" << std::endl;
        std::cout << "---\nTITLE: [Translated to " << target_lang << "]\n---\n";
        
        // Print a snippet of the original content to prove it transferred successfully
        std::cout << "[Translation Engine Simulated Output]\n";
        if (content.length() > 150) {
            std::cout << content.substr(0, 150) << "...\n";
        } else {
            std::cout << content << "\n";
        }
        std::cout << "===END_LANG===" << std::endl;
    }

    return 0;
}