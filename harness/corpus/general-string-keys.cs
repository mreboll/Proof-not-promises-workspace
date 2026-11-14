//@tag: general
using MessagePack;

namespace Corpus;

[MessagePackObject]
public class Settings
{
    [Key("host")] public string? Host { get; set; }
    [Key("port")] public int Port { get; set; }
    [Key("secure")] public bool Secure { get; set; }
}
