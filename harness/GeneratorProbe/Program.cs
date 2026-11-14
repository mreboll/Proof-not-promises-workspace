// GeneratorProbe: ejecuta el generador y los analizadores de MessagePack sobre cada snippet del corpus
// y escribe una salida canónica por caso (fuentes generadas ordenadas por HintName + diagnósticos ordenados).
// Uso: GeneratorProbe <corpusDir> <outDir>
//
// Formato de un snippet (.cs):
//   //@tag: general | issue-<id>
//   //@library   (opcional) lo que sigue se compila como OTRO ensamblado y se referencia solo como metadata
//   //@main      el código del proyecto analizado
using System.Collections.Immutable;
using System.Globalization;
using System.Reflection;
using System.Text;
using MessagePack;
using MessagePack.SourceGenerator;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.Diagnostics;

CultureInfo.DefaultThreadCurrentCulture = CultureInfo.InvariantCulture;
CultureInfo.DefaultThreadCurrentUICulture = CultureInfo.InvariantCulture;
CultureInfo.CurrentCulture = CultureInfo.InvariantCulture;
CultureInfo.CurrentUICulture = CultureInfo.InvariantCulture;

if (args.Length != 2)
{
    Console.Error.WriteLine("uso: GeneratorProbe <corpusDir> <outDir>");
    return 2;
}

string corpusDir = args[0];
string outDir = args[1];
Directory.CreateDirectory(outDir);

foreach (string file in Directory.GetFiles(corpusDir, "*.cs").OrderBy(f => f, StringComparer.Ordinal))
{
    string caseId = Path.GetFileNameWithoutExtension(file);
    string output;
    try
    {
        output = Probe.Run(File.ReadAllText(file));
    }
    catch (Exception ex)
    {
        output = $"=== probe-exception\n{ex.GetType().FullName}: {FirstLine(ex.Message)}\n";
    }

    File.WriteAllText(Path.Combine(outDir, caseId + ".txt"), output.Replace("\r\n", "\n"), new UTF8Encoding(false));
    Console.WriteLine(caseId);
}

return 0;

static string FirstLine(string text) => text.Split('\n')[0].TrimEnd('\r');

internal static class Probe
{
    private static readonly CSharpParseOptions ParseOptions = CSharpParseOptions.Default.WithLanguageVersion(LanguageVersion.Latest);

    private static readonly ImmutableArray<MetadataReference> BaseReferences = LoadBaseReferences();

    private static readonly ImmutableArray<DiagnosticAnalyzer> Analyzers = typeof(MessagePackGenerator).Assembly.GetTypes()
        .Where(t => !t.IsAbstract && typeof(DiagnosticAnalyzer).IsAssignableFrom(t) && t.GetCustomAttribute<DiagnosticAnalyzerAttribute>() is not null)
        .OrderBy(t => t.FullName, StringComparer.Ordinal)
        .Select(t => (DiagnosticAnalyzer)Activator.CreateInstance(t)!)
        .ToImmutableArray();

    public static string Run(string snippet)
    {
        (string? librarySource, string mainSource) = Split(snippet);
        var output = new StringBuilder();
        IEnumerable<MetadataReference> references = BaseReferences;

        if (librarySource is not null)
        {
            CSharpCompilation library = CreateCompilation("CorpusLibrary", "Library.cs", librarySource, references);
            using var image = new MemoryStream();
            var emit = library.Emit(image);
            if (!emit.Success)
            {
                output.Append("=== library-build-failed\n");
                AppendDiagnostics(output, emit.Diagnostics.Where(d => d.Severity == DiagnosticSeverity.Error));
                return output.ToString();
            }

            references = references.Append(MetadataReference.CreateFromImage(image.ToArray()));
        }

        CSharpCompilation compilation = CreateCompilation("CorpusApp", "Main.cs", mainSource, references);
        GeneratorDriver driver = CSharpGeneratorDriver.Create(
            new[] { new MessagePackGenerator().AsSourceGenerator() },
            parseOptions: ParseOptions);
        driver = driver.RunGeneratorsAndUpdateCompilation(compilation, out Compilation generated, out ImmutableArray<Diagnostic> generatorDiagnostics);

        foreach (GeneratedSourceResult source in driver.GetRunResult().Results
            .SelectMany(r => r.GeneratedSources)
            .OrderBy(s => s.HintName, StringComparer.Ordinal))
        {
            output.Append("=== generated: ").Append(source.HintName).Append('\n');
            output.Append(source.SourceText.ToString().Replace("\r\n", "\n")).Append('\n');
        }

        var withAnalyzers = generated.WithAnalyzers(
            Analyzers,
            new CompilationWithAnalyzersOptions(
                new AnalyzerOptions(ImmutableArray<AdditionalText>.Empty),
                onAnalyzerException: null,
                concurrentAnalysis: false,
                logAnalyzerExecutionTime: false));
        ImmutableArray<Diagnostic> analyzerDiagnostics = withAnalyzers.GetAnalyzerDiagnosticsAsync().GetAwaiter().GetResult();

        output.Append("=== diagnostics\n");
        AppendDiagnostics(
            output,
            generatorDiagnostics
                .Concat(analyzerDiagnostics)
                .Concat(generated.GetDiagnostics().Where(d => d.Severity == DiagnosticSeverity.Error)));
        return output.ToString();
    }

    private static (string? Library, string Main) Split(string snippet)
    {
        const string LibraryMarker = "//@library";
        const string MainMarker = "//@main";
        int main = snippet.IndexOf(MainMarker, StringComparison.Ordinal);
        int library = snippet.IndexOf(LibraryMarker, StringComparison.Ordinal);
        if (main < 0)
        {
            return (null, snippet);
        }

        string mainSource = snippet[(main + MainMarker.Length)..];
        string? librarySource = library >= 0 && library < main ? snippet[(library + LibraryMarker.Length)..main] : null;
        return (librarySource, mainSource);
    }

    private static CSharpCompilation CreateCompilation(string assemblyName, string path, string source, IEnumerable<MetadataReference> references)
        => CSharpCompilation.Create(
            assemblyName,
            new[] { CSharpSyntaxTree.ParseText(source, ParseOptions, path: path) },
            references,
            new CSharpCompilationOptions(
                OutputKind.DynamicallyLinkedLibrary,
                nullableContextOptions: NullableContextOptions.Enable,
                allowUnsafe: true,
                deterministic: true));

    private static void AppendDiagnostics(StringBuilder output, IEnumerable<Diagnostic> diagnostics)
    {
        foreach (string line in diagnostics.Select(Format).Distinct().OrderBy(l => l, StringComparer.Ordinal))
        {
            output.Append(line).Append('\n');
        }
    }

    private static string Format(Diagnostic d)
    {
        string location = d.Location.IsInSource
            ? FormatSpan(d.Location.GetLineSpan())
            : d.Location.Kind.ToString();
        string message = d.GetMessage(CultureInfo.InvariantCulture).Split('\n')[0].TrimEnd('\r');
        return $"{d.Id} {d.Severity} {location}: {message}";
    }

    private static string FormatSpan(FileLinePositionSpan span)
        => $"{span.Path}({span.StartLinePosition.Line + 1},{span.StartLinePosition.Character + 1})-({span.EndLinePosition.Line + 1},{span.EndLinePosition.Character + 1})";

    private static ImmutableArray<MetadataReference> LoadBaseReferences()
    {
        // Ensamblados gestionados del runtime compartido (TPA), filtrados a su carpeta: excluye las
        // dependencias del propio probe (Roslyn, el generador). Ordenados para que sea determinista.
        string runtimeDir = Path.GetDirectoryName(typeof(object).Assembly.Location)!;
        var framework = ((string)AppContext.GetData("TRUSTED_PLATFORM_ASSEMBLIES")!)
            .Split(Path.PathSeparator)
            .Where(p => string.Equals(Path.GetDirectoryName(p), runtimeDir, StringComparison.OrdinalIgnoreCase))
            .OrderBy(p => Path.GetFileName(p), StringComparer.OrdinalIgnoreCase);
        var messagePack = new[]
        {
            typeof(MessagePackObjectAttribute).Assembly.Location,
            typeof(MessagePackSerializer).Assembly.Location,
        };
        return framework.Concat(messagePack)
            .Select(p => (MetadataReference)MetadataReference.CreateFromFile(p))
            .ToImmutableArray();
    }
}
