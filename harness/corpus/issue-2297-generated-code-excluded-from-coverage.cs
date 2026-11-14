//@tag: issue-2297
using MessagePack;

namespace Corpus;

[MessagePackObject]
public class Covered
{
    [Key(0)] public int Id { get; set; }
}

[GeneratedMessagePackResolver]
public partial class CoverageResolver { }
