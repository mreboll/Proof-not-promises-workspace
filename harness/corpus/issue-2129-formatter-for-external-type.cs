//@tag: issue-2129
//@library
namespace Lib
{
    public class ExternalPerson
    {
        public int Id { get; set; }
        public string? Label { get; set; }
    }
}
//@main
using MessagePack;
using MessagePack.Formatters;
using Lib;

namespace App
{
    [GeneratedMessagePackFormatter]
    public partial class ExternalPersonFormatter : IMessagePackFormatter<ExternalPerson>
    {
    }
}
